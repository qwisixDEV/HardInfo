"""Antivirus products reported by Windows Security Center."""

from typing import Any, Mapping

from hardinfo.models.health import SecurityProductInfo
from .disks import _records


def collect_security(payload: Mapping[str, Any]) -> tuple[SecurityProductInfo, ...]:
    """Build a read-only antivirus overview from the WMI payload."""
    return tuple(
        SecurityProductInfo.from_wmi(item) for item in _records(payload.get("av"))
    )
