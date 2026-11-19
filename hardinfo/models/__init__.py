"""Data models describing collected system information."""

from hardinfo.models.hardware import (
    CPUInfo,
    GPUInfo,
    HardwareProfile,
    MemoryInfo,
    OSInfo,
    PlatformInfo,
)
from hardinfo.models.health import (
    DiskBenchmarkResult,
    DiskInfo,
    LicenseInfo,
    NetworkInfo,
    SecurityProductInfo,
    SystemHealthSnapshot,
)
from hardinfo.models.registry import BackupEntry, RegistryTarget, TweakResult

__all__ = [
    "CPUInfo",
    "GPUInfo",
    "HardwareProfile",
    "MemoryInfo",
    "OSInfo",
    "PlatformInfo",
    "BackupEntry",
    "RegistryTarget",
    "TweakResult",
    "DiskBenchmarkResult",
    "DiskInfo",
    "LicenseInfo",
    "NetworkInfo",
    "SecurityProductInfo",
    "SystemHealthSnapshot",
]
