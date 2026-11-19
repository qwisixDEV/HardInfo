"""Automatic dependency bootstrap for the HARDINFO application.

Preserves the original monolithic script behaviour: if the GUI/runtime
libraries are missing, they are installed with pip on first import.
"""

import subprocess
import sys

_INSTALLED = False


def ensure_dependencies() -> None:
    """Install PySide6 and psutil when they are not available yet."""
    global _INSTALLED
    if _INSTALLED:
        return

    try:
        import PySide6.QtCore  # noqa: F401
        import PySide6.QtGui  # noqa: F401
        import PySide6.QtWidgets  # noqa: F401
        import psutil  # noqa: F401
        if sys.platform == "win32":
            import winreg  # noqa: F401
    except ImportError:
        print("[SYSTEM] Отсутствуют необходимые библиотеки. Запуск автоустановщика...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PySide6", "psutil"]
        )

    _INSTALLED = True
