"""Local host, user and network interface collector."""

import logging
import os
import socket
from typing import Any, Mapping

import psutil

from hardinfo.models.health import NetworkInfo
from hardinfo.models.hardware import _text


def collect_network(_payload: Mapping[str, Any] | None = None) -> NetworkInfo:
    """Collect local network data without making external requests."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "Н/Д"
    try:
        username = _text(os.getlogin())
    except Exception:
        username = _text(os.environ.get("USERNAME") or os.environ.get("USER"))

    addresses: list[str] = []
    interfaces: list[str] = []
    for name, stats in (psutil.net_if_stats() or {}).items():
        interfaces.append(f"{name} ({'up' if stats.isup else 'down'}, {stats.speed} Mbps)")
    for _name, infos in (psutil.net_if_addrs() or {}).items():
        for info in infos:
            if info.family == socket.AF_INET and info.address not in addresses:
                addresses.append(info.address)
            elif info.family == socket.AF_INET6 and info.address not in addresses:
                addresses.append(info.address)

    connected = any(
        stats.isup
        for stats in (psutil.net_if_stats() or {}).values()
    )
    logging.debug("[SYSTEM] Сеть: %s, интерфейсов: %s", addresses, len(interfaces))
    return NetworkInfo(
        hostname=_text(hostname),
        username=username,
        ip_addresses=tuple(addresses),
        interfaces=tuple(interfaces),
        is_connected=connected,
    )
