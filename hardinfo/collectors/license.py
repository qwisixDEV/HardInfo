"""Read-only Windows license status collector."""

import logging
import subprocess
from typing import Any, Mapping

from hardinfo.constants import POWERSHELL_TIMEOUT_SECONDS
from hardinfo.models.health import LicenseInfo


def collect_license(payload: Mapping[str, Any]) -> LicenseInfo:
    """Prefer WMI license data and fall back to ``slmgr /xpr``."""
    info = LicenseInfo.from_wmi_payload(payload)
    if info.activated:
        return info

    try:
        result = subprocess.run(
            ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/xpr"],
            capture_output=True,
            text=True,
            errors="ignore",
            timeout=POWERSHELL_TIMEOUT_SECONDS,
        )
        detail = " ".join((result.stdout or "").split())
        if detail:
            return LicenseInfo(
                name=info.name,
                status="detail",
                activated="активирована" in detail.lower() or "activated" in detail.lower(),
                expiration=detail[:160],
                partial=False,
            )
    except Exception as exc:
        logging.debug("[SYSTEM] slmgr status unavailable: %s", exc)
    return info
