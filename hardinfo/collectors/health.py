"""Aggregates dynamic health data into a single typed snapshot."""

import logging
import time
from typing import Any, Mapping

import psutil
from PySide6.QtCore import QThread, Signal

from hardinfo.constants import LOAD_WARNING_PERCENT
from hardinfo.models.health import (
    DiskBenchmarkResult,
    LicenseInfo,
    SystemHealthSnapshot,
)

from .disks import collect_disks
from .license import collect_license
from .network import collect_network
from .security import collect_security


def collect_health_snapshot(
    payload: Mapping[str, Any] | None = None,
    benchmark: DiskBenchmarkResult | None = None,
    use_slsmgr: bool = False,
) -> SystemHealthSnapshot:
    """Collect disks, network, security and license in one pass."""
    payload = payload or {}
    disks = collect_disks(payload)
    network = collect_network(payload)
    security = collect_security(payload)
    license_info = (
        collect_license(payload)
        if use_slsmgr
        else LicenseInfo.from_wmi_payload(payload)
    )

    try:
        uptime = max(time.time() - psutil.boot_time(), 0.0)
    except Exception as exc:
        logging.debug("[SYSTEM] Uptime unavailable: %s", exc)
        uptime = 0.0

    warnings: list[str] = []
    for disk in disks:
        warnings.extend(f"{disk.mountpoint or disk.model}: {text}" for text in disk.warnings)
    try:
        load = psutil.cpu_percent(interval=0.05)
        if load >= LOAD_WARNING_PERCENT:
            warnings.append(f"Загрузка ЦП {load:.0f}%")
    except Exception:
        pass

    return SystemHealthSnapshot(
        uptime_seconds=uptime,
        disks=disks,
        network=network,
        security=security,
        license=license_info,
        benchmark=benchmark,
        warnings=tuple(warnings),
    )


class HealthInfoThread(QThread):
    """Collects dynamic health data without blocking the GUI thread."""

    health_loaded_signal = Signal(object)

    def __init__(self, payload: Mapping[str, Any] | None = None):
        super().__init__()
        self.payload = dict(payload or {})

    def run(self) -> None:
        try:
            snapshot = collect_health_snapshot(self.payload)
            self.health_loaded_signal.emit(snapshot)
        except Exception as exc:  # pragma: no cover - defensive GUI guard
            logging.error("[ERROR] Health collection failed: %s", exc)
