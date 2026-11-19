"""System and hardware profile collector (WMI/CIM via PowerShell)."""

import base64
import json
import logging
import subprocess
from typing import Any

from PySide6.QtCore import QThread, Signal

WMI_SCRIPT = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "SilentlyContinue"
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, InstallDate | ConvertTo-Json -Compress
$pc = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model | ConvertTo-Json -Compress
$bios = Get-CimInstance Win32_BIOS | Select-Object SerialNumber, Manufacturer, SMBIOSBIOSVersion | ConvertTo-Json -Compress
$cpu = Get-CimInstance Win32_Processor | Select-Object Name, MaxClockSpeed, NumberOfCores, NumberOfLogicalProcessors, L2CacheSize, L3CacheSize, CurrentVoltage | ConvertTo-Json -Compress
$board = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product | ConvertTo-Json -Compress
$ram = Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, PartNumber, SerialNumber, Speed, Capacity, SMBIOSMemoryType | ConvertTo-Json -Compress
$gpu = Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, VideoProcessor | ConvertTo-Json -Compress
$disks = Get-CimInstance Win32_DiskDrive | Select-Object Model, MediaType, InterfaceType, Size, Status | ConvertTo-Json -Compress
$disk_health = Get-CimInstance -Namespace root\\wmi -ClassName MSStorageDriver_FailurePredictStatus | Select-Object InstanceName, PredictFailure | ConvertTo-Json -Compress
$smart = Get-CimInstance -Namespace root\\wmi -ClassName MSStorageDriver_ATAPISmartData | Select-Object InstanceName, VendorSpecific | ConvertTo-Json -Compress
$av = Get-CimInstance -Namespace root\\SecurityCenter2 -ClassName AntiVirusProduct | Select-Object displayName, productState | ConvertTo-Json -Compress
$license = Get-CimInstance SoftwareLicensingProduct -Filter "PartialProductKey is not null" | Select-Object Name, LicenseStatus, GracePeriodRemaining, PartialProductKey | ConvertTo-Json -Compress

# Локализационно-независимый опрос сетевого и медийного драйвера напрямую через PnP-классы
$net = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceClass -eq "NET" } | Select-Object DeviceName, DriverVersion | ConvertTo-Json -Compress
$audio = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceClass -eq "MEDIA" } | Select-Object DeviceName, DriverVersion | ConvertTo-Json -Compress

$payload = @{
    os = $os; pc = $pc; bios = $bios; cpu = $cpu; board = $board; ram = $ram; gpu = $gpu; net = $net; audio = $audio
    disks = $disks; disk_health = $disk_health; smart = $smart; av = $av; license = $license
}
ConvertTo-Json $payload -Depth 4 -Compress
"""


def collect_system_snapshot(timeout: int = 15) -> dict[str, Any]:
    """Collect a normalized hardware snapshot; return an empty dict on failure."""
    utf16_bytes = WMI_SCRIPT.encode("utf-16le")
    b64_str = base64.b64encode(utf16_bytes).decode("ascii")
    cmd = f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {b64_str}"

    res = subprocess.run(cmd, capture_output=True, shell=True, timeout=timeout)
    if res.returncode != 0 or not res.stdout:
        return {}

    raw_text = res.stdout.decode("utf-8", errors="ignore").strip()
    data = json.loads(raw_text)

    for key in data.keys():
        if isinstance(data[key], str) and data[key].strip():
            try:
                inner = json.loads(data[key])
                data[key] = inner if isinstance(inner, list) else [inner]
            except Exception:
                data[key] = []
        elif not isinstance(data[key], list):
            data[key] = []

    return data


class SystemInfoThread(QThread):
    hardware_loaded_signal = Signal(dict)

    def run(self) -> None:
        logging.info("[SYSTEM] Фоновый сбор WMI характеристик (Language-Independent)...")
        try:
            data = collect_system_snapshot()
            self.hardware_loaded_signal.emit(data)
            logging.info(
                "[SYSTEM] Профиль оборудования собран." if data
                else "[SYSTEM] WMI недоступен, используется резервный сбор данных."
            )
        except Exception as e:
            logging.error(f"[ERROR] Ошибка WMI сбора: {e}")
