"""Asynchronous driver download thread bypassing regional mirrors.
"""

import os
import urllib.request
from PySide6.QtCore import QThread, Signal


class DriverDownloadThread(QThread):
    progress_signal = Signal(str)
    done_signal = Signal(bool, str)

    def __init__(self, vendor: str):
        super().__init__()
        self.vendor = vendor

    def run(self):
        self.progress_signal.emit("[DOWNLOAD] Подготовка к обходу ограничений...")
        try:
            if self.vendor == "nvidia":
                mirror_url = "https://download.nvidia.com.tw/Windows/555.99/555.99-desktop-win10-win11-64bit-international-dch-whql.exe"
                local_filename = "NVIDIA-Driver-Bypass.exe"
            elif self.vendor == "intel":
                mirror_url = "https://downloadmirror.intel.com/28425/a/Intel-Driver-and-Support-Assistant-Installer.exe"
                local_filename = "Intel-DSA-Bypass.exe"
            elif self.vendor == "realtek_audio":
                mirror_url = "https://downloadmirror.intel.com/783856/a/HDAudio-Realtek-Win10-Win11.exe"
                local_filename = "Realtek-Audio-Bypass.exe"
            else:
                mirror_url = "https://downloadmirror.intel.com/785532/a/WiFi-Intel-Win10-Win11.exe"
                local_filename = "Intel-WiFi-Bypass.exe"

            self.progress_signal.emit(f"[DOWNLOAD] Старт прямого скачивания: {self.vendor.upper()}")

            req = urllib.request.Request(
                mirror_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )

            with urllib.request.urlopen(req, timeout=30) as response, open(local_filename, 'wb') as out_file:
                meta = response.info()
                file_size = int(meta.get("Content-Length", 0))
                self.progress_signal.emit(f"[DOWNLOAD] Размер: {file_size / (1024**2):.1f} MB. Загрузка...")

                block_sz = 1024 * 64
                downloaded = 0
                while True:
                    buffer = response.read(block_sz)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)

            self.progress_signal.emit(f"[DOWNLOAD] Скачивание успешно завершено: {local_filename}")
            os.startfile(local_filename)
            self.done_signal.emit(True, f"Пакет {local_filename} загружен и запущен!")
        except Exception as e:
            self.progress_signal.emit(f"[ERROR] Ошибка прямого соединения: {e}")
            self.done_signal.emit(False, str(e))
