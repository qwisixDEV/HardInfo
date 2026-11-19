"""Transactional registry tweak tests with an in-memory winreg stub."""

import json

import pytest
import winreg

from hardinfo.utils import registry


class FakeKey:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


@pytest.fixture
def fake_registry(monkeypatch, tmp_path):
    store = {"Value": (0, winreg.REG_DWORD)}
    monkeypatch.setattr(registry, "REGISTRY_BACKUP_FILE", str(tmp_path / "backup.json"))
    monkeypatch.setattr(
        registry,
        "TWEAKS_DB",
        {
            "dummy": {
                "title": "Dummy tweak",
                "reg": [("HKCU", r"Software\HardInfoTest", "Value", winreg.REG_DWORD, 1)],
            }
        },
    )
    monkeypatch.setattr(registry.winreg, "OpenKey", lambda *a, **k: FakeKey(store))
    monkeypatch.setattr(registry.winreg, "CreateKeyEx", lambda *a, **k: FakeKey(store))
    monkeypatch.setattr(
        registry.winreg,
        "QueryValueEx",
        lambda key, name: (store[name] if name in store else (_ for _ in ()).throw(FileNotFoundError())),
    )
    monkeypatch.setattr(
        registry.winreg, "SetValueEx", lambda key, name, reserved, kind, value: store.__setitem__(name, (value, kind))
    )
    monkeypatch.setattr(registry.winreg, "DeleteValue", lambda key, name: store.pop(name, None))
    return store, tmp_path / "backup.json"


def test_plan_tweak_does_not_write(fake_registry):
    store, _backup = fake_registry
    plan = registry.SafeRegistryBackup.plan_tweak("dummy")
    assert plan and "->" in plan[0]
    assert store["Value"][0] == 0


def test_apply_and_revert_tweak(fake_registry):
    store, backup_path = fake_registry
    result = registry.apply_tweak("dummy", True)
    assert result.ok and result.changed == 1
    assert store["Value"][0] == 1
    assert "HKCU\\Software\\HardInfoTest\\Value" in json.loads(backup_path.read_text("utf-8"))

    reverted = registry.revert_tweak("dummy")
    assert reverted.ok and reverted.changed == 1
    assert store["Value"][0] == 0
    assert json.loads(backup_path.read_text("utf-8")) == {}


def test_dry_run_never_writes(fake_registry):
    store, backup_path = fake_registry
    result = registry.apply_tweak("dummy", True, dry_run=True)
    assert result.dry_run and result.changed == 1
    assert store["Value"][0] == 0
    assert not backup_path.exists()


def test_restore_all_clears_backup(fake_registry):
    store, backup_path = fake_registry
    registry.apply_tweak("dummy", True)
    assert registry.SafeRegistryBackup.restore_all()[0] is True
    assert store["Value"][0] == 0
    assert json.loads(backup_path.read_text("utf-8")) == {}


def test_corrupt_backup_is_quarantined(fake_registry):
    _store, backup_path = fake_registry
    backup_path.write_text("{not json", encoding="utf-8")
    assert registry.SafeRegistryBackup.load_backup() == {}
    assert list(backup_path.parent.glob("backup.json.corrupt.*"))
