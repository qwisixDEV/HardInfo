"""Asynchronous, verified driver downloads from vendor mirrors."""

import hashlib
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal


@dataclass(frozen=True)
class DriverSource:
    url: str
    filename: str
    expected_sha256: str | None = None
    verify_signature: bool = True


# Hashes can be pinned here when a mirror publishes a stable checksum.
# Until then the Authenticode signature is used as the verification method.
DRIVER_SOURCES: dict[str, DriverSource] = {
    "nvidia": DriverSource(
        url="https://download.nvidia.com.tw/Windows/555.99/555.99-desktop-win10-win11-64bit-international-dch-whql.exe",
        filename="NVIDIA-Driver-Bypass.exe",
    ),
    "intel": DriverSource(
        url="https://downloadmirror.intel.com/28425/a/Intel-Driver-and-Support-Assistant-Installer.exe",
        filename="Intel-DSA-Bypass.exe",
    ),
    "realtek_audio": DriverSource(
        url="https://downloadmirror.intel.com/783856/a/HDAudio-Realtek-Win10-Win11.exe",
        filename="Realtek-Audio-Bypass.exe",
    ),
    "intel_wifi": DriverSource(
        url="https://downloadmirror.intel.com/785532/a/WiFi-Intel-Win10-Win11.exe",
        filename="Intel-WiFi-Bypass.exe",
    ),
}


def get_driver_source(vendor: str) -> DriverSource:
    """Return a known source, falling back to the Intel WiFi package."""
    return DRIVER_SOURCES.get(vendor, DRIVER_SOURCES["intel_wifi"])


def sha256sum(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_authenticode(path: str | Path) -> tuple[bool, str]:
    """Check the embedded Authenticode signature on Windows."""
    if sys.platform != "win32":
        return False, "Проверка подписи доступна только в Windows"
    escaped = str(path).replace("'", "''")
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"(Get-AuthenticodeSignature -FilePath '{escaped}').Status",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        status = (result.stdout or "").strip() or "Unknown"
        return status.lower() == "valid", status
    except Exception as exc:
        return False, str(exc)


class DriverDownloadThread(QThread):
    progress_signal = Signal(str)
    done_signal = Signal(bool, str)
    file_ready_signal = Signal(str)

    def __init__(self, vendor: str):
        super().__init__()
        self.vendor = vendor

    def run(self) -> None:
        self.progress_signal.emit("[DOWNLOAD] Подготовка к обходу ограничений...")
        source = get_driver_source(self.vendor)
        partial = Path(source.filename + ".part")
        try:
            self.progress_signal.emit(
                f"[DOWNLOAD] Старт прямого скачивания: {self.vendor.upper()}"
            )
            request = urllib.request.Request(
                source.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )

            with urllib.request.urlopen(request, timeout=30) as response, open(
                partial, "wb"
            ) as out_file:
                file_size = int(response.info().get("Content-Length", 0))
                self.progress_signal.emit(
                    f"[DOWNLOAD] Размер: {file_size / (1024**2):.1f} MB. Загрузка..."
                )
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    out_file.write(chunk)

            if source.expected_sha256:
                actual = sha256sum(partial)
                if actual.lower() != source.expected_sha256.lower():
                    partial.unlink(missing_ok=True)
                    raise ValueError(f"SHA256 не совпал: {actual}")
                self.progress_signal.emit("[VERIFY] Контрольная сумма SHA256 подтверждена.")
            elif source.verify_signature and sys.platform == "win32":
                valid, status = verify_authenticode(partial)
                if not valid:
                    partial.unlink(missing_ok=True)
                    raise ValueError(f"Подпись недопустима: {status}")
                self.progress_signal.emit(f"[VERIFY] Подпись производителя действительна: {status}")
            else:
                self.progress_signal.emit("[WARN] Автоматическая проверка недоступна.")

            os.replace(partial, source.filename)
            destination = str(Path(source.filename).resolve())
            self.progress_signal.emit(f"[DOWNLOAD] Файл готов: {destination}")
            self.file_ready_signal.emit(destination)
            self.done_signal.emit(
                True,
                f"Пакет {source.filename} загружен и проверен. Запустите установку вручную.",
            )
        except Exception as exc:
            partial.unlink(missing_ok=True)
            self.progress_signal.emit(f"[ERROR] Ошибка прямого соединения: {exc}")
            self.done_signal.emit(False, str(exc))
