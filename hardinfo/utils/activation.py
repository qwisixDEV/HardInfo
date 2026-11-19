"""Asynchronous Windows activation via KMS.
"""

import subprocess
from PySide6.QtCore import QThread, Signal


class WindowsActivationThread(QThread):
    log_signal = Signal(str)
    done_signal = Signal(bool, str)

    def __init__(self, key: str, kms_server: str = "kms.digiboy.ir"):
        super().__init__()
        self.key = key
        self.kms_server = kms_server

    def run(self):
        steps = [
            (f"slmgr.vbs /ipk {self.key}", "Установка GVLK ключа..."),
            (f"slmgr.vbs /skms {self.kms_server}", f"Подключение к KMS серверу {self.kms_server}..."),
            ("slmgr.vbs /ato", "Запрос активации...")
        ]

        for cmd, desc in steps:
            self.log_signal.emit(f"[KMS] {desc}")
            try:
                res = subprocess.run(
                    f"cscript //nologo C:\\Windows\\System32\\{cmd}",
                    capture_output=True,
                    shell=True,
                    timeout=12
                )
                out = res.stdout.decode('cp866', errors='ignore').strip()
                if out:
                    self.log_signal.emit(out)
            except subprocess.TimeoutExpired:
                self.log_signal.emit("[WARN] Запрос превысил тайм-аут.")
            self.msleep(1000)

        self.done_signal.emit(True, "Процедура активации Windows выполнена!")
