"""Physical disk, partition usage and S.M.A.R.T. collectors."""

import logging
from typing import Any, Mapping

import psutil

from hardinfo.models.hardware import _int, _text
from hardinfo.models.health import DiskInfo

# S.M.A.R.T. attribute identifiers used by the ATA vendor data block.
_TEMPERATURE_IDS = {190, 194}
_REMAINING_LIFE_IDS = {202, 233}


def _records(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    return []


def _drive_number(name: str) -> int | None:
    """Extract the physical drive index from a WMI InstanceName."""
    marker = "physicaldrive"
    lowered = name.lower()
    if marker not in lowered:
        return None
    tail = lowered.split(marker, 1)[1].strip()
    digits = "".join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else None


def parse_smart(raw: Any) -> dict[int, tuple[float | None, float | None]]:
    """Return ``{drive_index: (temperature, remaining_life_percent)}``."""
    parsed: dict[int, tuple[float | None, float | None]] = {}
    for item in _records(raw):
        index = _drive_number(str(item.get("InstanceName") or ""))
        if index is None:
            continue
        vendor = item.get("VendorSpecific")
        if not isinstance(vendor, (list, tuple)):
            continue
        values = [_int(byte, -1) for byte in vendor]
        temperature: float | None = None
        remaining: float | None = None
        for offset in range(0, len(values) - 1, 12):
            attribute = values[offset]
            current = values[offset + 1]
            if attribute in _TEMPERATURE_IDS and 0 < current < 200:
                temperature = float(current)
            if attribute in _REMAINING_LIFE_IDS and 0 <= current <= 100:
                remaining = float(current) if attribute == 233 else float(100 - current)
        parsed[index] = (temperature, remaining)
    return parsed


def _partition_usage() -> list[tuple[str, int, int, float]]:
    """Return ``(mountpoint, used, free, percent)`` for local fixed drives."""
    usage: list[tuple[str, int, int, float]] = []
    for partition in psutil.disk_partitions(all=False):
        if "cdrom" in partition.opts.lower() or partition.fstype.lower() in {"", "squashfs"}:
            continue
        try:
            data = psutil.disk_usage(partition.mountpoint)
        except (PermissionError, OSError) as exc:
            logging.debug("[SYSTEM] Partition %s unavailable: %s", partition.mountpoint, exc)
            continue
        usage.append(
            (
                partition.mountpoint,
                data.used,
                data.free,
                round(data.percent, 1),
            )
        )
    return usage


def collect_disks(payload: Mapping[str, Any]) -> tuple[DiskInfo, ...]:
    """Build disk cards from the WMI payload and local partition usage."""
    smart = parse_smart(payload.get("smart"))
    health_by_drive: dict[int, str] = {}
    for item in _records(payload.get("disk_health")):
        index = _drive_number(str(item.get("InstanceName") or ""))
        if index is None:
            continue
        health_by_drive[index] = (
            "PREDICT FAILURE" if bool(item.get("PredictFailure")) else "OK"
        )

    physical = _records(payload.get("disks"))
    partitions = _partition_usage()
    disks: list[DiskInfo] = []

    for index, item in enumerate(physical):
        temperature, remaining = smart.get(index, (None, None))
        mountpoint, used, free, percent = (
            partitions[index] if index < len(partitions) else ("", 0, 0, 0.0)
        )
        disks.append(
            DiskInfo(
                model=_text(item.get("Model"), "Неизвестный диск"),
                media_type=_text(item.get("MediaType"), "Fixed"),
                interface=_text(item.get("InterfaceType")),
                size_bytes=_int(item.get("Size")),
                status=_text(item.get("Status")),
                health=health_by_drive.get(index, "недоступно"),
                mountpoint=mountpoint,
                used_bytes=used,
                free_bytes=free,
                used_percent=percent,
                temperature=temperature,
                wear_percent=100.0 - remaining if remaining is not None else None,
            )
        )

    if not disks and partitions:
        for mountpoint, used, free, percent in partitions:
            disks.append(
                DiskInfo(
                    model=mountpoint,
                    media_type="partition",
                    interface="неизвестно",
                    size_bytes=used + free,
                    status="OK",
                    health="недоступно",
                    mountpoint=mountpoint,
                    used_bytes=used,
                    free_bytes=free,
                    used_percent=percent,
                )
            )
    return tuple(disks)
