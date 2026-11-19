"""Collector and model tests for disks, network, security and license."""

import psutil

from hardinfo.collectors import collect_disks, parse_smart
from hardinfo.models import (
    DiskBenchmarkResult,
    LicenseInfo,
    NetworkInfo,
    SecurityProductInfo,
    SystemHealthSnapshot,
)


def _vendor_block(attribute_id, current_value):
    block = [0] * 12
    block[0] = attribute_id
    block[1] = current_value
    return block


def test_parse_smart_temperature_and_wear():
    vendor = _vendor_block(194, 42) + _vendor_block(233, 85)
    parsed = parse_smart([{"InstanceName": r"\\.\PhysicalDrive0", "VendorSpecific": vendor}])
    assert parsed[0] == (42.0, 85.0)


def test_collect_disks_uses_partition_usage(monkeypatch):
    class Usage:
        used = 40
        free = 60
        percent = 40.0

    class Partition:
        mountpoint = "C:\\"
        fstype = "NTFS"
        opts = "rw,fixed"

    monkeypatch.setattr(psutil, "disk_partitions", lambda **_kwargs: [Partition()])
    monkeypatch.setattr(psutil, "disk_usage", lambda _path: Usage())
    payload = {
        "disks": [{"Model": "SSD", "MediaType": "Fixed", "Size": 100, "Status": "OK"}],
        "disk_health": [{"InstanceName": r"\\.\PhysicalDrive0", "PredictFailure": False}],
    }
    disks = collect_disks(payload)
    assert len(disks) == 1
    assert disks[0].mountpoint == "C:\\"
    assert disks[0].used_percent == 40.0
    assert disks[0].health == "OK"


def test_security_product_state_bits():
    product = SecurityProductInfo.from_wmi({"displayName": "Defender", "productState": 0x41000})
    assert product.enabled is True
    assert product.up_to_date is True
    outdated = SecurityProductInfo.from_wmi({"displayName": "AV", "productState": 0x60100})
    assert outdated.up_to_date is False


def test_license_from_wmi():
    info = LicenseInfo.from_wmi_payload(
        {"license": [{"Name": "Windows", "LicenseStatus": 1, "GracePeriodRemaining": 0}]}
    )
    assert info.activated is True
    assert info.expiration == "бессрочно"


def test_health_snapshot_serializes():
    snapshot = SystemHealthSnapshot(
        uptime_seconds=7200,
        network=NetworkInfo("PC", "user", ("127.0.0.1",), ("Lo",), True),
        benchmark=DiskBenchmarkResult(150, 500.0, 400.0, 1.0),
    )
    data = snapshot.to_dict()
    assert data["network"]["hostname"] == "PC"
    assert data["benchmark"]["read_mbps"] == 500.0
    assert "uptime_seconds" in data
