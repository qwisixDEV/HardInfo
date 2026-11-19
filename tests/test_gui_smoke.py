"""Offscreen GUI smoke test for the refactored main window."""

from PySide6.QtWidgets import QApplication

from hardinfo.ui import HardInfoMainWindow


def test_main_window_builds_all_tabs():
    app = QApplication.instance() or QApplication([])
    window = HardInfoMainWindow()
    try:
        assert window.tabs.count() == 6
        assert window.sys_subtabs.count() == 4
        assert [window.sys_subtabs.tabText(i) for i in range(4)] == [
            "Обзор",
            "Диски",
            "Сеть",
            "Безопасность",
        ]
        assert len(window.toggles) == 24
        assert window.btn_disk_benchmark is not None
        assert window.btn_benchmark_cancel is not None
        app.processEvents()
    finally:
        window.close()
