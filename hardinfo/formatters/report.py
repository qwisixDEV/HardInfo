"""Formatting helpers and report export for hardware profiles."""

import json
from pathlib import Path
from typing import Any, Mapping

from hardinfo.constants import APP_VERSION
from hardinfo.models import HardwareProfile, SystemHealthSnapshot


def format_cpu_voltage(raw_value: Any) -> str:
    """Convert a raw WMI voltage value into a human-readable string."""
    if not raw_value:
        return "1.20 V"
    try:
        value = float(raw_value)
        if value > 100:
            value /= 1000.0
        elif value > 5:
            value /= 10.0
        return f"{value:.2f} V"
    except (TypeError, ValueError):
        return "1.20 V"


def format_memory_capacity(total_bytes: int) -> str:
    """Format RAM capacity in gigabytes."""
    return f"{total_bytes // (1024**3)} GB"


def format_vram(adapter_ram_bytes: int) -> str:
    """Format GPU memory, handling the signed WMI AdapterRAM representation."""
    value = adapter_ram_bytes
    if isinstance(value, int) and value < 0:
        value = 4294967296 + value
    megabytes = value // (1024**2) if isinstance(value, int) else 0
    return f"{megabytes} MB" if megabytes < 1024 else f"{megabytes // 1024} GB"


def format_uptime(seconds: float) -> str:
    """Format an uptime value as days/hours/minutes."""
    minutes = int(seconds // 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    return f"{days} д, {hours} ч, {minutes} мин"


def format_bytes(size_bytes: int) -> str:
    """Format a byte count using binary units."""
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def render_text_report(
    profile: HardwareProfile,
    sensors: Mapping[str, Any] | None = None,
    lang: str = "ru",
    health: SystemHealthSnapshot | None = None,
) -> str:
    """Render a portable plain-text hardware report."""
    lines = [
        "HARDINFO — Hardware Report" if lang == "en" else "HARDINFO — Отчёт об оборудовании",
        "=" * 40,
    ]
    sections: list[tuple[str, tuple[tuple[str, Any], ...]]] = [
        (
            "Operating System" if lang == "en" else "Операционная система",
            (
                ("OS", profile.os.name),
                ("Version", profile.os.version),
                ("Architecture", profile.os.architecture),
                ("Installed", profile.os.install_date),
            ),
        ),
        (
            "Platform" if lang == "en" else "Аппаратная платформа",
            (
                ("Vendor", profile.platform.manufacturer),
                ("Model", profile.platform.model),
                ("Board", profile.platform.board_product),
                ("BIOS", profile.platform.bios_version),
                ("BIOS Serial", profile.platform.bios_serial),
            ),
        ),
        (
            "CPU" if lang == "en" else "Процессор",
            (
                ("Model", profile.cpu.name),
                ("Voltage", format_cpu_voltage(profile.cpu.voltage)),
                ("Cores / Threads", f"{profile.cpu.cores} / {profile.cpu.logical_processors}"),
                ("L2 / L3 cache", f"{profile.cpu.l2_cache_kb} / {profile.cpu.l3_cache_kb} KB"),
            ),
        ),
        (
            "Memory" if lang == "en" else "Оперативная память",
            (
                ("Capacity", format_memory_capacity(profile.memory.total_bytes)),
                ("Type", profile.memory.ram_type),
                ("Speed", f"{profile.memory.speed} MHz"),
                ("Modules", profile.memory.module_count),
            ),
        ),
        (
            "GPU" if lang == "en" else "Видеоадаптер",
            (
                ("Model", profile.gpu.name),
                ("Driver", profile.gpu.driver_version),
                ("Video processor", profile.gpu.video_processor),
                ("VRAM", format_vram(profile.gpu.adapter_ram_bytes)),
            ),
        ),
        (
            "Drivers" if lang == "en" else "Драйверы",
            (
                ("Network", profile.network_driver),
                ("Audio", profile.audio_driver),
            ),
        ),
    ]

    for title, rows in sections:
        lines.append("")
        lines.append(f"[{title}]")
        lines.extend(f"  {key}: {value}" for key, value in rows)

    if health:
        lines.append("")
        lines.append("[" + ("Health" if lang == "en" else "Состояние системы") + "]")
        lines.append(f"  Uptime: {format_uptime(health.uptime_seconds)}")
        if health.license:
            lines.append(f"  License: {health.license.name} ({health.license.status}, {health.license.expiration})")

        lines.append("")
        lines.append("[" + ("Disks" if lang == "en" else "Диски") + "]")
        if health.disks:
            for disk in health.disks:
                lines.append(
                    f"  {disk.model} [{disk.mountpoint or '-'}] "
                    f"size={format_bytes(disk.size_bytes)} "
                    f"used={disk.used_percent}% health={disk.health} "
                    f"temp={disk.temperature if disk.temperature is not None else 'н/д'}°C"
                )
        else:
            lines.append("  " + ("No disks detected" if lang == "en" else "Диски не обнаружены"))

        lines.append("")
        lines.append("[" + ("Network" if lang == "en" else "Сеть") + "]")
        if health.network:
            net = health.network
            lines.append(f"  Host: {net.hostname}")
            lines.append(f"  User: {net.username}")
            lines.append(f"  IPs: {', '.join(net.ip_addresses) or '-'}")
            lines.append(f"  Connected: {net.is_connected}")
            lines.extend(f"  IF: {item}" for item in net.interfaces)

        lines.append("")
        lines.append("[" + ("Security" if lang == "en" else "Безопасность") + "]")
        if health.security:
            for product in health.security:
                lines.append(
                    f"  {product.name}: enabled={product.enabled}, "
                    f"up_to_date={product.up_to_date}, state=0x{product.product_state:X}"
                )
        else:
            lines.append("  " + ("No antivirus products reported" if lang == "en" else "Антивирусы не обнаружены"))

        if health.benchmark:
            lines.append("")
            lines.append("[" + ("Disk benchmark" if lang == "en" else "Бенчмарк диска") + "]")
            lines.append(f"  {health.benchmark.summary}")

        if health.warnings:
            lines.append("")
            lines.append("[" + ("Warnings" if lang == "en" else "Предупреждения") + "]")
            lines.extend(f"  ! {warning}" for warning in health.warnings)

    if sensors:
        lines.append("")
        lines.append("[" + ("Live sensors" if lang == "en" else "Текущие показатели") + "]")
        lines.extend(f"  {key}: {value}" for key, value in sensors.items())

    return "\n".join(lines) + "\n"


def export_report(
    profile: HardwareProfile,
    path: str | Path,
    fmt: str = "text",
    sensors: Mapping[str, Any] | None = None,
    lang: str = "ru",
    health: SystemHealthSnapshot | None = None,
) -> Path:
    """Write a hardware report to ``path`` in text or JSON format."""
    destination = Path(path)
    if fmt == "json":
        payload = {
            "schema": 2,
            "app_version": APP_VERSION,
            "profile": {
                "os": vars(profile.os),
                "platform": vars(profile.platform),
                "cpu": {**vars(profile.cpu), "voltage": format_cpu_voltage(profile.cpu.voltage)},
                "memory": {
                    **vars(profile.memory),
                    "capacity": format_memory_capacity(profile.memory.total_bytes),
                },
                "gpu": {
                    **vars(profile.gpu),
                    "vram": format_vram(profile.gpu.adapter_ram_bytes),
                },
                "network_driver": profile.network_driver,
                "audio_driver": profile.audio_driver,
            },
            "health": health.to_dict() if health else None,
            "sensors": dict(sensors or {}),
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2)
    elif fmt == "text":
        content = render_text_report(profile, sensors, lang, health)
    else:
        raise ValueError(f"Unsupported report format: {fmt}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination
