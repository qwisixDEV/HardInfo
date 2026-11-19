"""Hardware collectors: WMI snapshots, live sensors and spec parsers."""

from hardinfo.collectors.gpu import (
    HAS_PYNVML,
    get_amd_intel_gpu_usage_light,
    get_nvidia_detailed_sensors,
)
from hardinfo.collectors.sensors import SensorMonitorThread
from hardinfo.collectors.specs import estimate_ram_timings, parse_hardware_specs_dynamically
from hardinfo.collectors.system import SystemInfoThread, collect_system_snapshot

__all__ = [
    "HAS_PYNVML",
    "get_amd_intel_gpu_usage_light",
    "get_nvidia_detailed_sensors",
    "SensorMonitorThread",
    "estimate_ram_timings",
    "parse_hardware_specs_dynamically",
    "SystemInfoThread",
    "collect_system_snapshot",
]
