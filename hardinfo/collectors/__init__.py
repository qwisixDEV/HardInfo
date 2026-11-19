"""Hardware collectors: WMI snapshots, live sensors, health and spec parsers."""

from hardinfo.collectors.benchmark import DiskBenchmarkThread, run_disk_benchmark
from hardinfo.collectors.disks import collect_disks, parse_smart
from hardinfo.collectors.gpu import (
    HAS_PYNVML,
    get_amd_intel_gpu_usage_light,
    get_nvidia_detailed_sensors,
)
from hardinfo.collectors.health import HealthInfoThread, collect_health_snapshot
from hardinfo.collectors.license import collect_license
from hardinfo.collectors.network import collect_network
from hardinfo.collectors.security import collect_security
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
    "collect_disks",
    "parse_smart",
    "collect_health_snapshot",
    "HealthInfoThread",
    "collect_license",
    "collect_network",
    "collect_security",
    "run_disk_benchmark",
    "DiskBenchmarkThread",
]
