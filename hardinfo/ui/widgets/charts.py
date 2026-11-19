"""Real-time sparkline line chart widget for CPU and RAM history.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt


class RealtimeLineChart(QWidget):
    def __init__(self, color_line, parent=None):
        super().__init__(parent)
        self.color_line = QColor(color_line)
        self.data = [0] * 40
        self.setMinimumSize(210, 100)

    def add_value(self, val):
        self.data.pop(0)
        self.data.append(val)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()

        painter.fillRect(0, 0, width, height, QColor("#050506"))

        pen_grid = QPen(QColor("#121214"), 1, Qt.DashLine)
        painter.setPen(pen_grid)
        for i in range(1, 4):
            y = int((height / 4) * i)
            painter.drawLine(0, y, width, y)

        pen_line = QPen(self.color_line, 2)
        painter.setPen(pen_line)
        path = QPainterPath()
        x_step = width / (len(self.data) - 1)
        for i, val in enumerate(self.data):
            x = i * x_step
            val_clamped = max(0, min(100, val))
            y = height - (val_clamped / 100.0 * (height - 12)) - 6
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.drawPath(path)
