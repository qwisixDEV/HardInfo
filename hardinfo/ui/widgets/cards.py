"""Hover card component with glowing border accents.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from hardinfo.constants import COLOR_CARD, COLOR_BORDER, COLOR_TEXT_SEC, COLOR_ACCENT_TEAL


class HoverCard(QFrame):
    def __init__(self, title_ru="", title_en="", accent_color=COLOR_ACCENT_TEAL, app_parent=None):
        super().__init__(app_parent)
        self.setObjectName("Card")
        self.accent_color = accent_color
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {COLOR_CARD};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(6)

        if title_ru:
            self.lbl_title = QLabel()
            self.lbl_title.setStyleSheet(
                f"color: {COLOR_TEXT_SEC}; font-size: 10px; font-weight: bold; border: none; background: transparent;"
            )
            self.main_layout.addWidget(self.lbl_title)
            if app_parent and hasattr(app_parent, "register_tr"):
                app_parent.register_tr(self.lbl_title, title_ru.upper(), title_en.upper())
            else:
                self.lbl_title.setText(title_ru.upper())

    def enterEvent(self, event):
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {COLOR_CARD};
                border: 1px solid {self.accent_color};
                border-radius: 8px;
            }}
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {COLOR_CARD};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        super().leaveEvent(event)
