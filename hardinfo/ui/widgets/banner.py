"""Administrator privilege elevation warning banner.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class AdminWarningBanner(QFrame):
    def __init__(self, parent, relaunch_callback, **kwargs):
        super().__init__(parent)
        self.setObjectName("Banner")
        self.setStyleSheet("""
            QFrame#Banner {
                background-color: #211510;
                border: 1px solid #F59E0B;
                border-radius: 6px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 10, 15, 10)

        lbl_tag = QLabel("[ВНИМАНИЕ]" if getattr(parent, "current_lang", "ru") == "ru" else "[WARNING]")
        lbl_tag.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        parent.register_tr(lbl_tag, "[ВНИМАНИЕ]", "[WARNING]")
        lay.addWidget(lbl_tag)

        info_text_ru = (
            "ОГРАНИЧЕННЫЙ РЕЖИМ (Запуск без прав Администратора).\n"
            "Заблокировано: Изменение твиков, электропитание, KMS-активация."
        )
        info_text_en = (
            "LIMITED MODE (Run without Admin privileges).\n"
            "Blocked: Registry tweaks, power plans, KMS activation."
        )
        lbl_text = QLabel()
        lbl_text.setStyleSheet("color: #FFE4D0; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        lbl_text.setWordWrap(True)
        parent.register_tr(lbl_text, info_text_ru, info_text_en)
        lay.addWidget(lbl_text, stretch=1)

        btn_elevate = QPushButton()
        btn_elevate.setFixedSize(140, 28)
        btn_elevate.setStyleSheet("""
            QPushButton {
                background-color: #3a251a;
                color: #FFE4D0;
                border: 1px solid #FFB03A;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #523525;
            }
        """)
        btn_elevate.clicked.connect(relaunch_callback)
        parent.register_tr(btn_elevate, "Повысить права", "Elevate Privileges")
        lay.addWidget(btn_elevate)
