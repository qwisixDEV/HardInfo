"""Formatting helpers and report export for hardware profiles."""

import json
from pathlib import Path
from typing import Any, Mapping

from hardinfo.models import HardwareProfile


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


def render_text_report(
    profile: HardwareProfile,
    sensors: Mapping[str, Any] | None = None,
    lang: str = "ru",
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
) -> Path:
    """Write a hardware report to ``path`` in text or JSON format."""
    destination = Path(path)
    if fmt == "json":
        payload = {
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
            "sensors": dict(sensors or {}),
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2)
    elif fmt == "text":
        content = render_text_report(profile, sensors, lang)
    else:
        raise ValueError(f"Unsupported report format: {fmt}")

    destination.write_text(content, encoding="utf-8")
    return destination
