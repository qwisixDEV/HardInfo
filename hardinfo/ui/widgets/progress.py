"""Custom elegant progress bar with dynamic color indicators.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from hardinfo.constants import COLOR_ACCENT_TEAL, COLOR_ACCENT_RED


class ElegantProgressBar(QWidget):
    def __init__(self, width_bar=220, height_bar=6, parent=None):
        super().__init__(parent)
        self.width_bar = width_bar
        self.height_bar = height_bar
        self.value = 0
        self.setMinimumSize(width_bar, height_bar + 4)

    def set_value(self, val):
        self.value = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(0, 2, self.width_bar, self.height_bar, QColor("#121214"))

        percent = max(0, min(100, self.value))
        fill_width = int((percent / 100) * self.width_bar)
        if fill_width > 0:
            color = (
                QColor(COLOR_ACCENT_TEAL) if percent < 60
                else (QColor("#F59E0B") if percent < 85 else QColor(COLOR_ACCENT_RED))
            )
            painter.fillRect(0, 2, fill_width, self.height_bar, color)
