"""Windows Registry backup and transactional tweak management."""

import json
import logging
import os
import time
from typing import Any

import winreg

from hardinfo.constants import REGISTRY_BACKUP_FILE
from hardinfo.models.registry import BackupEntry, RegistryTarget, TweakResult
from hardinfo.tweaks_db import TWEAKS_DB

MISSING = "__missing__"


def _hive(hive_name: str) -> int:
    return winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE


class SafeRegistryBackup:
    """Stores original values and applies/reverts tweaks with a safety net."""

    @staticmethod
    def load_backup() -> dict[str, Any]:
        if not os.path.exists(REGISTRY_BACKUP_FILE):
            return {}
        try:
            with open(REGISTRY_BACKUP_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            quarantine = f"{REGISTRY_BACKUP_FILE}.corrupt.{int(time.time())}"
            try:
                os.replace(REGISTRY_BACKUP_FILE, quarantine)
            except Exception:
                pass
            logging.error("[ERROR] Бэкап повреждён, файл отложен в %s: %s", quarantine, exc)
            return {}

    @staticmethod
    def save_backup(data: dict[str, Any]) -> None:
        """Write the backup atomically to avoid half-written JSON files."""
        temporary = f"{REGISTRY_BACKUP_FILE}.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4, ensure_ascii=False)
            os.replace(temporary, REGISTRY_BACKUP_FILE)
        except Exception as exc:
            logging.error("[ERROR] Ошибка бэкапа реестра: %s", exc)

    @staticmethod
    def read_value(
        hive_name: str, path: str, value_name: str, expected_type: int = winreg.REG_DWORD
    ) -> tuple[Any, int] | None:
        """Return ``(value, type)``; ``(MISSING, type)`` when the value is absent."""
        try:
            with winreg.OpenKey(_hive(hive_name), path, 0, winreg.KEY_READ) as key:
                value, value_type = winreg.QueryValueEx(key, value_name)
                return value, value_type
        except FileNotFoundError:
            return MISSING, expected_type
        except Exception as exc:
            logging.warning("[SYSTEM] Не удалось прочитать %s\\%s: %s", path, value_name, exc)
            return None

    @staticmethod
    def write_value(
        hive_name: str, path: str, value_name: str, value_type: int, value: Any
    ) -> bool:
        try:
            try:
                key = winreg.CreateKeyEx(_hive(hive_name), path, 0, winreg.KEY_SET_VALUE)
            except Exception:
                key = winreg.OpenKey(_hive(hive_name), path, 0, winreg.KEY_SET_VALUE)
            with key:
                winreg.SetValueEx(key, value_name, 0, value_type, value)
            return True
        except Exception as exc:
            logging.error("[ERROR] Запись %s\\%s не удалась: %s", path, value_name, exc)
            return False

    @staticmethod
    def delete_value(hive_name: str, path: str, value_name: str) -> bool:
        try:
            with winreg.OpenKey(_hive(hive_name), path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, value_name)
            return True
        except FileNotFoundError:
            return True
        except Exception as exc:
            logging.error("[ERROR] Удаление %s\\%s не удалось: %s", path, value_name, exc)
            return False

    @classmethod
    def backup_value(
        cls, hive_name: str, path: str, value_name: str, expected_type: int = winreg.REG_DWORD
    ) -> None:
        """Back up one value (used by the startup manager and other actions)."""
        current = cls.read_value(hive_name, path, value_name, expected_type)
        if current is None:
            return
        value, value_type = current
        backup_data = cls.load_backup()
        key_str = f"{hive_name}\\{path}\\{value_name}"
        if key_str in backup_data:
            return
        backup_data[key_str] = BackupEntry(
            hive_name, path, value_name, value, value_type
        ).to_mapping()
        cls.save_backup(backup_data)
        logging.info("[SYSTEM] Создан бэкап: %s -> %s", key_str, value)

    @staticmethod
    def _targets(tweak_id: str) -> list[RegistryTarget]:
        info = TWEAKS_DB[tweak_id]
        return [
            RegistryTarget(hive, path, value_name, value_type, value)
            for hive, path, value_name, value_type, value in info["reg"]
        ]

    @classmethod
    def plan_tweak(cls, tweak_id: str) -> list[str]:
        """Describe planned writes without changing anything."""
        lines = []
        for target in cls._targets(tweak_id):
            current = cls.read_value(
                target.hive, target.path, target.value_name, target.expected_type
            )
            if current is None:
                lines.append(f"{target.key}: чтение недоступно")
            else:
                lines.append(f"{target.key}: {current[0]!r} -> {target.desired_value!r}")
        return lines

    @classmethod
    def apply_tweak(cls, tweak_id: str, enable: bool, dry_run: bool = False) -> TweakResult:
        """Apply or revert every value of a tweak; only changed values are written."""
        try:
            targets = cls._targets(tweak_id)
        except KeyError:
            return TweakResult(tweak_id, enable, 0, ("неизвестный твик",), dry_run)

        backup_data = cls.load_backup()
        changed = 0
        failed: list[str] = []
        backup_dirty = False

        for target in targets:
            current = cls.read_value(
                target.hive, target.path, target.value_name, target.expected_type
            )
            if current is None:
                failed.append(target.value_name)
                continue
            current_value, current_type = current

            if enable:
                if current_value == target.desired_value and current_type == target.expected_type:
                    continue

                existing = backup_data.get(target.key)
                if existing is not None:
                    original = BackupEntry.from_mapping(target.key, existing)
                    if original.value != current_value:
                        backup_data[target.key] = BackupEntry(
                            target.hive,
                            target.path,
                            target.value_name,
                            current_value,
                            current_type,
                        ).to_mapping()
                        backup_dirty = True
                else:
                    backup_data[target.key] = BackupEntry(
                        target.hive,
                        target.path,
                        target.value_name,
                        current_value,
                        current_type,
                    ).to_mapping()
                    backup_dirty = True

                if dry_run:
                    changed += 1
                    continue
                if cls.write_value(
                    target.hive,
                    target.path,
                    target.value_name,
                    target.expected_type,
                    target.desired_value,
                ):
                    changed += 1
                else:
                    failed.append(target.value_name)
            else:
                raw_entry = backup_data.get(target.key)
                if raw_entry is None:
                    continue
                entry = BackupEntry.from_mapping(target.key, raw_entry)

                if entry.value == MISSING:
                    if dry_run:
                        changed += 1
                        continue
                    restored = cls.delete_value(target.hive, target.path, target.value_name)
                else:
                    if current_value == entry.value and current_type == entry.type:
                        backup_data.pop(target.key, None)
                        backup_dirty = True
                        continue
                    if dry_run:
                        changed += 1
                        continue
                    restored = cls.write_value(
                        target.hive, target.path, target.value_name, entry.type, entry.value
                    )

                if restored:
                    changed += 1
                    backup_data.pop(target.key, None)
                    backup_dirty = True
                else:
                    failed.append(target.value_name)

        if backup_dirty and not dry_run:
            cls.save_backup(backup_data)

        return TweakResult(tweak_id, enable, changed, tuple(failed), dry_run)

    @classmethod
    def revert_tweak(cls, tweak_id: str, dry_run: bool = False) -> TweakResult:
        return cls.apply_tweak(tweak_id, enable=False, dry_run=dry_run)

    @classmethod
    def restore_all(cls) -> tuple[bool, str]:
        backup_data = cls.load_backup()
        if not backup_data:
            return True, "Нет сохраненных резервных копий."

        success_count = 0
        failed_count = 0
        for key_str, raw_item in backup_data.items():
            item = BackupEntry.from_mapping(key_str, raw_item)
            if item.value == MISSING:
                restored = cls.delete_value(item.hive, item.path, item.value_name)
            else:
                restored = cls.write_value(
                    item.hive, item.path, item.value_name, item.type, item.value
                )
            if restored:
                success_count += 1
            else:
                failed_count += 1
                logging.error("[ERROR] Не удалось восстановить %s", key_str)

        if failed_count == 0:
            cls.save_backup({})
            return True, f"Все твики реестра ({success_count}) возвращены по умолчанию."
        return False, f"Восстановлено: {success_count}. Сбоев: {failed_count}."


def apply_tweak(tweak_id: str, enable: bool, dry_run: bool = False) -> TweakResult:
    """Module-level shortcut used by the UI."""
    return SafeRegistryBackup.apply_tweak(tweak_id, enable, dry_run)


def revert_tweak(tweak_id: str, dry_run: bool = False) -> TweakResult:
    """Module-level shortcut used by the UI."""
    return SafeRegistryBackup.revert_tweak(tweak_id, dry_run)
