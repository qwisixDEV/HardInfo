"""Typed data models for hardware information collected from WMI."""

from dataclasses import dataclass
from typing import Any, Mapping

from hardinfo.utils.helpers import clean_system_string


def _first(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """Return the first record of a WMI section or an empty mapping."""
    items = payload.get(key) or []
    if isinstance(items, dict):
        items = [items]
    return items[0] if items and isinstance(items[0], dict) else {}


def _text(value: Any, default: str = "Н/Д") -> str:
    """Normalize a WMI string for display."""
    return clean_system_string(str(value)) if value not in (None, "") else default


def _int(value: Any, default: int = 0) -> int:
    """Best-effort conversion of a WMI numeric value."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class OSInfo:
    name: str
    version: str
    architecture: str


@dataclass(frozen=True)
class PlatformInfo:
    manufacturer: str
    model: str
    bios_serial: str
    bios_version: str
    board_manufacturer: str
    board_product: str


@dataclass(frozen=True)
class CPUInfo:
    name: str
    voltage: Any


@dataclass(frozen=True)
class MemoryInfo:
    total_bytes: int
    speed: int
    module_count: int
    ram_type: str


@dataclass(frozen=True)
class GPUInfo:
    name: str
    driver_version: str
    video_processor: str
    adapter_ram_bytes: int


@dataclass(frozen=True)
class HardwareProfile:
    """Normalized snapshot of the machine, independent of the UI layer."""

    os: OSInfo
    platform: PlatformInfo
    cpu: CPUInfo
    memory: MemoryInfo
    gpu: GPUInfo
    network_driver: str
    audio_driver: str

    @classmethod
    def from_wmi_payload(cls, payload: Mapping[str, Any]) -> "HardwareProfile":
        """Build a profile from the raw payload produced by the collector."""
        os_data = _first(payload, "os")
        pc_data = _first(payload, "pc")
        bios_data = _first(payload, "bios")
        board_data = _first(payload, "board")
        cpu_data = _first(payload, "cpu")
        gpu_data = _first(payload, "gpu")
        net_data = _first(payload, "net")
        audio_data = _first(payload, "audio")
        modules = payload.get("ram") or []

        type_value = _first(payload, "ram").get("SMBIOSMemoryType")
        ram_type = "DDR4" if type_value == 26 else ("DDR5" if type_value == 34 else "DDR4/DDR5")
        total_bytes = sum(_int(module.get("Capacity")) for module in modules)
        speed = _int(next(iter(modules), {}).get("Speed"), 3200)

        return cls(
            os=OSInfo(
                name=_text(os_data.get("Caption"), "Windows"),
                version=_text(os_data.get("Version")),
                architecture=_text(os_data.get("OSArchitecture")),
            ),
            platform=PlatformInfo(
                manufacturer=_text(pc_data.get("Manufacturer")),
                model=_text(pc_data.get("Model")),
                bios_serial=_text(bios_data.get("SerialNumber")),
                bios_version=_text(bios_data.get("SMBIOSBIOSVersion")),
                board_manufacturer=_text(board_data.get("Manufacturer")),
                board_product=_text(board_data.get("Product")),
            ),
            cpu=CPUInfo(
                name=str(cpu_data.get("Name") or "Н/Д"),
                voltage=cpu_data.get("CurrentVoltage"),
            ),
            memory=MemoryInfo(
                total_bytes=total_bytes,
                speed=speed,
                module_count=len(modules),
                ram_type=ram_type,
            ),
            gpu=GPUInfo(
                name=str(gpu_data.get("Name") or "Н/Д"),
                driver_version=_text(gpu_data.get("DriverVersion")),
                video_processor=_text(gpu_data.get("VideoProcessor")),
                adapter_ram_bytes=_int(gpu_data.get("AdapterRAM")),
            ),
            network_driver=_text(net_data.get("DriverVersion")),
            audio_driver=_text(audio_data.get("DriverVersion")),
        )
