"""Security regressions: OEM validation, driver verification, SHA256."""

import hashlib

import pytest

from hardinfo.ui.main_window import OEM_DRIVER_PATTERN
from hardinfo.utils import drivers
from hardinfo.utils.drivers import (
    DriverSource,
    get_driver_source,
    sha256sum,
    verify_authenticode,
)


@pytest.mark.parametrize("value", ["oem12.inf; calc.exe", "oem.inf", "oem12.exe", "../oem1.inf"])
def test_oem_injection_rejected(value):
    assert OEM_DRIVER_PATTERN.fullmatch(value) is None


@pytest.mark.parametrize("value", ["oem12.inf", "OEM123.INF", "oem0.inf"])
def test_oem_valid_name(value):
    assert OEM_DRIVER_PATTERN.fullmatch(value) is not None


def test_sha256sum(tmp_path):
    target = tmp_path / "driver.bin"
    target.write_bytes(b"hardinfo")
    assert sha256sum(target) == hashlib.sha256(b"hardinfo").hexdigest()


def test_verify_authenticode_uses_powershell(monkeypatch):
    calls = []

    class Result:
        stdout = "Valid"
        stderr = ""

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(drivers.subprocess, "run", fake_run)
    valid, status = verify_authenticode("C:\\driver.exe")
    assert valid is True
    assert status == "Valid"
    assert calls and calls[0][0] == "powershell"


def test_driver_sources_are_registered():
    assert {"nvidia", "intel", "realtek_audio", "intel_wifi"} <= set(drivers.DRIVER_SOURCES)
    assert isinstance(get_driver_source("unknown"), DriverSource)
