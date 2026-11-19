"""Centralized Windows administrator privilege helpers."""

import ctypes
import sys
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def is_admin() -> bool:
    """Return True when the current process has administrator privileges."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def require_admin(parent: Any, action_ru: str, action_en: str) -> bool:
    """Show one consistent warning when an action needs elevated rights."""
    if is_admin():
        return True

    from PySide6.QtWidgets import QMessageBox

    lang = getattr(parent, "current_lang", "ru")
    QMessageBox.warning(
        parent,
        "Права администратора" if lang == "ru" else "Admin Privileges",
        action_ru if lang == "ru" else action_en,
    )
    return False
