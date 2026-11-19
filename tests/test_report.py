"""Report schema and content tests."""

import json

from hardinfo.formatters import export_report, format_uptime
from hardinfo.models import (
    CPUInfo,
    DiskInfo,
    GPUInfo,
    HardwareProfile,
    LicenseInfo,
    MemoryInfo,
    OSInfo,
    PlatformInfo,
    SystemHealthSnapshot,
)


def _profile():
    return HardwareProfile(
        os=OSInfo("Windows 11", "10.0", "64-bit", "2026-01-01"),
        platform=PlatformInfo("Vendor", "Model", "SN", "BIOS", "Board", "Product"),
        cpu=CPUInfo("CPU", 12, 8, 16, 1024, 16384),
        memory=MemoryInfo(16 * 1024**3, 3200, 2, "DDR4"),
        gpu=GPUInfo("GPU", "1.0", "Processor", 1024**3),
        network_driver="net",
        audio_driver="audio",
    )


def _health():
    return SystemHealthSnapshot(
        uptime_seconds=90061,
        disks=(DiskInfo("SSD", "Fixed", "NVMe", 10**12, "OK", "OK", "C:\\", 0, 10**12, 0.0, 40.0),),
        license=LicenseInfo("Windows", "activated", True, "бессрочно", False),
        warnings=("тест",),
    )


def test_format_uptime():
    assert format_uptime(90061) == "1 д, 1 ч, 1 мин"


def test_json_report_schema_2(tmp_path):
    destination = export_report(_profile(), tmp_path / "report.json", fmt="json", health=_health())
    payload = json.loads(destination.read_text("utf-8"))
    assert payload["schema"] == 2
    assert payload["health"]["disks"][0]["model"] == "SSD"
    assert payload["profile"]["cpu"]["cores"] == 8
    assert payload["profile"]["os"]["install_date"] == "2026-01-01"


def test_text_report_includes_new_sections(tmp_path):
    destination = export_report(_profile(), tmp_path / "report.txt", fmt="text", health=_health())
    text = destination.read_text("utf-8")
    assert "Uptime" in text
    assert "[Disks]" in text or "[Диски]" in text
    assert "S.M.A.R.T." not in text  # short disk summary, not a per-attribute dump
    assert "тест" in text
