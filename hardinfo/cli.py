"""Command-line entry point for HARDINFO.

Without arguments the original GUI is launched.  Optional flags allow
exporting a hardware report without opening a window.
"""

import argparse
import ctypes
import logging
import sys

from hardinfo.constants import APP_VERSION, LOG_FILE, MUTEX_NAME
from hardinfo.utils.logging import setup_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="HardInfo.py",
        description=f"HARDINFO {APP_VERSION} — диагностика и оптимизация системы",
    )
    parser.add_argument(
        "--report",
        choices=("text", "json"),
        help="сохранить отчёт об оборудовании вместо запуска GUI",
    )
    parser.add_argument(
        "--output",
        default="hardinfo_report.txt",
        help="путь к файлу отчёта (по умолчанию: hardinfo_report.txt)",
    )
    return parser


def _is_already_running() -> bool:
    """Create the application mutex and report whether another instance exists."""
    if sys.platform != "win32":
        return False
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, True, MUTEX_NAME)
    return kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def _warn_already_running() -> None:
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    QMessageBox.warning(None, "Внимание", "HARDINFO уже запущен на данном компьютере!")
    del app
    raise SystemExit(0)


def _export_report(fmt: str, output: str) -> int:
    from hardinfo.collectors import collect_health_snapshot, collect_system_snapshot
    from hardinfo.formatters import export_report
    from hardinfo.models import HardwareProfile

    payload = collect_system_snapshot()
    profile = HardwareProfile.from_wmi_payload(payload)
    health = collect_health_snapshot(payload, use_slsmgr=True)
    destination = export_report(profile, output, fmt=fmt, health=health)
    print(f"[SYSTEM] Отчёт сохранён: {destination}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the application (or export a report) and return an exit code."""
    args, _unknown = _build_parser().parse_known_args(argv)

    if args.report:
        setup_logging(LOG_FILE)
        return _export_report(args.report, args.output)

    if _is_already_running():
        _warn_already_running()

    setup_logging(LOG_FILE)
    logging.info("[SYSTEM] Запуск HARDINFO %s", APP_VERSION)

    from PySide6.QtWidgets import QApplication

    from hardinfo.ui import HardInfoMainWindow

    app = QApplication(sys.argv)
    window = HardInfoMainWindow()
    window.show()
    return app.exec()
