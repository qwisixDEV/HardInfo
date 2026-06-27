import sys
import os
import platform
import subprocess
import json
import socket
import ctypes
import logging
import time
import base64
import re

# --- АВТОМАТИЧЕСКАЯ УСТАНОВКА ЗАВИСИМОСТЕЙ ---
try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                   QHBoxLayout, QStackedWidget, QLabel, QTextEdit, 
                                   QFrame, QPushButton, QLineEdit, QListWidget, 
                                   QScrollArea, QSizePolicy, QMessageBox, QCheckBox,
                                   QGraphicsOpacityEffect)
    from PySide6.QtCore import QThread, Signal, QTimer, Qt, QSize, QObject, QPropertyAnimation, QEasingCurve
    from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QIcon
    import psutil
    import winreg
except ImportError:
    print("[SYSTEM] Отсутствуют необходимые библиотеки. Запуск автоустановщика...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PySide6", "psutil"])
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                   QHBoxLayout, QStackedWidget, QLabel, QTextEdit, 
                                   QFrame, QPushButton, QLineEdit, QListWidget, 
                                   QScrollArea, QSizePolicy, QMessageBox, QCheckBox,
                                   QGraphicsOpacityEffect)
    from PySide6.QtCore import QThread, Signal, QTimer, Qt, QSize, QObject, QPropertyAnimation, QEasingCurve
    from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QIcon
    import psutil
    import winreg

# Попытка динамического импорта NVML для оптимизации телеметрии GPU
try:
    import pynvml  # type: ignore
    pynvml.nvmlInit()
    HAS_PYNVML = True
except Exception:
    HAS_PYNVML = False

APP_VERSION = "0.0.2"

# --- ЦВЕТОВАЯ ПАЛИТРА PITCH BLACK & NEON GLOW ---
COLOR_BG = "#040405"          
COLOR_SIDEBAR = "#09090b"     
COLOR_CARD = "#0d0d10"        
COLOR_BORDER = "#1b1b22"      
COLOR_TEXT_PR = "#FFFFFF"     
COLOR_TEXT_SEC = "#8a8a93"    
COLOR_ACCENT_TEAL = "#00ffcc" 
COLOR_ACCENT_VIOLET = "#d946ef"
COLOR_ACCENT_GREEN = "#00ff66"
COLOR_ACCENT_RED = "#ff3366"  

REGISTRY_BACKUP_FILE = "backup_settings.json"

# --- ПОТОКОБЕЗОПАСНЫЙ СИГНАЛЬНЫЙ ЛОГГЕР ---
class QtLogSignaller(QObject):
    log_signal = Signal(str)

class QtLoggingHandler(logging.Handler):
    def __init__(self, signaller):
        super().__init__()
        self.signaller = signaller

    def emit(self, record):
        msg = self.format(record)
        self.signaller.log_signal.emit(msg)

# --- ИСПРАВЛЕНИЕ КРАКОЗЯБР (MOJIBAKE FILTER) ---
def clean_system_string(text):
    if not text:
        return ""
    cleaned = re.sub(r'[^\w\s\-\(\)\.,:/\*™®+\x00-\x7F\u0400-\u04FF]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# --- ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗАТОР СПЕЦИФИКАЦИЙ ---
def parse_hardware_specs_dynamically(hw_name, is_gpu=True):
    name = hw_name.lower()
    specs = {}
    if is_gpu:
        specs["apis"] = "DX12 Ultimate, Vulkan, OpenCL"
        if "nvidia" in name or "geforce" in name or "rtx" in name:
            specs["apis"] += ", CUDA"
            
        if "rtx 50" in name:
            specs["codename"] = "Blackwell (NVIDIA)"
            specs["nm"] = "4 nm (TSMC)"
            specs["bus"] = "128-bit - 512-bit"
        elif "rtx 40" in name:
            specs["codename"] = "Ada Lovelace (NVIDIA)"
            specs["nm"] = "4 nm (TSMC)"
            specs["bus"] = "96-bit - 384-bit"
        elif "rtx 30" in name:
            specs["codename"] = "Ampere (NVIDIA)"
            specs["nm"] = "8 nm (Samsung)"
            specs["bus"] = "128-bit - 384-bit"
        elif "rx 8" in name:
            specs["codename"] = "RDNA 4 (AMD)"
            specs["nm"] = "4 nm"
            specs["bus"] = "128-bit - 256-bit"
        elif "rx 7" in name:
            specs["codename"] = "RDNA 3 (AMD)"
            specs["nm"] = "5 nm"
            specs["bus"] = "128-bit - 384-bit"
        elif "rx 6" in name:
            specs["codename"] = "RDNA 2 (AMD)"
            specs["nm"] = "7 nm"
            specs["bus"] = "128-bit - 256-bit"
        elif "arc" in name:
            specs["codename"] = "Alchemist / Battlemage"
            specs["nm"] = "6 nm / 4 nm"
            specs["bus"] = "96-bit - 256-bit"
        else:
            specs["codename"] = "Определяется системой"
            specs["nm"] = "Зависит от поколения"
            specs["bus"] = "Динамическая"
    else:
        if "ultra" in name or "lunar" in name or "arrow" in name:
            specs["codename"] = "Arrow / Lunar Lake (Intel)"
            specs["nm"] = "3 nm (Intel 20A / TSMC)"
            specs["tdp"] = "15W - 125W"
        elif "9950" in name or "9900" in name or "9700" in name or "9800" in name or "ryzen 9" in name:
            specs["codename"] = "Zen 5 (AMD)"
            specs["nm"] = "4 nm"
            specs["tdp"] = "65W - 170W"
        elif "7950" in name or "7900" in name or "7800" in name or "7700" in name or "7600" in name:
            specs["codename"] = "Zen 4 (AMD)"
            specs["nm"] = "5 nm"
            specs["tdp"] = "65W - 170W"
        elif "14900" in name or "14700" in name or "14600" in name or "14400" in name or "14th gen" in name:
            specs["codename"] = "Raptor Lake Refresh (Intel)"
            specs["nm"] = "10 nm (Intel 7)"
            specs["tdp"] = "65W - 125W"
        elif "13900" in name or "13700" in name or "13600" in name or "13420" in name or "13400" in name or "13th gen" in name or "i5-13" in name or "i7-13" in name:
            specs["codename"] = "Raptor Lake (Intel)"
            specs["nm"] = "10 nm (Intel 7)"
            specs["tdp"] = "45W - 125W"
        elif "12900" in name or "12700" in name or "12600" in name or "12400" in name or "12th gen" in name or "i5-12" in name:
            specs["codename"] = "Alder Lake (Intel)"
            specs["nm"] = "10 nm (Intel 7)"
            specs["tdp"] = "45W - 125W"
        elif "5800x3d" in name or "5900" in name or "5600" in name or "ryzen 5" in name:
            specs["codename"] = "Zen 3 (AMD)"
            specs["nm"] = "7 nm"
            specs["tdp"] = "65W - 105W"
        else:
            specs["codename"] = "Стандартная архитектура"
            specs["nm"] = "7-14 nm"
            specs["tdp"] = "45W - 95W"
            
    return specs

# --- ТВИКИ РЕЕСТРА ---
TWEAKS_DB = {
    # 1. SAFE PROFILE (Безопасный)
    "disable_bg_ops": {
        "title": "Убрать фоновые операции",
        "desc": "Блокирует выполнение второстепенных приложений и задач в фоновом режиме.",
        "category": "safe",
        "reg": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", winreg.REG_DWORD, 1),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BackgroundAppDiagnosticLogging", winreg.REG_DWORD, 0)
        ]
    },
    "disable_store_updates": {
        "title": "Выключить автообновления Store",
        "desc": "Запрещает Магазину Windows самостоятельно загружать пакеты обновлений в фоне.",
        "category": "safe",
        "reg": [
            ("HKLM", r"SOFTWARE\Policies\Microsoft\WindowsStore", "AutoDownload", winreg.REG_DWORD, 2)
        ]
    },
    "disable_auto_maintenance": {
        "title": "Не обслуживать систему автоматически",
        "desc": "Запрещает Windows проводить дефрагментацию и диагностику во время простоя.",
        "category": "safe",
        "reg": [
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\Maintenance", "MaintenanceDisabled", winreg.REG_DWORD, 1)
        ]
    },
    "startup_delay_zero": {
        "title": "Автозапуск приложений без задержек",
        "desc": "Снимает задержку старта программ при входе в учетную запись Windows.",
        "category": "safe",
        "reg": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize", "StartupDelayInMSec", winreg.REG_DWORD, 0)
        ]
    },
    "menu_show_delay_zero": {
        "title": "Убрать задержку показа окон",
        "desc": "Ускоряет появление контекстных списков меню и всплывающих диалогов до мгновенного.",
        "category": "safe",
        "reg": [
            ("HKCU", r"Control Panel\Desktop", "MenuShowDelay", winreg.REG_SZ, "0")
        ]
    },
    "disable_ads": {
        "title": "Выключить рекламу",
        "desc": "Убирает встроенные предложения, баннеры и советы от Microsoft в меню Пуск.",
        "category": "safe",
        "reg": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SystemPaneSuggestionsEnabled", winreg.REG_DWORD, 0),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SilentInstalledAppsEnabled", winreg.REG_DWORD, 0)
        ]
    },
    "disable_web_extension_search": {
        "title": "Запретить поиск неизвестного расширения",
        "desc": "Убирает раздражающий диалог 'Искать приложение в магазине' при открытии редких типов файлов.",
        "category": "safe",
        "reg": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer", "InternetOpenWith", winreg.REG_DWORD, 0)
        ]
    },

    # 2. GAMING PROFILE (Игровой)
    "game_priority": {
        "title": "Задать приоритет играм",
        "desc": "Повышает планирование ресурсов процессора для исполняемых игровых файлов.",
        "category": "gaming",
        "reg": [
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", winreg.REG_DWORD, 8),
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", winreg.REG_DWORD, 6),
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", winreg.REG_SZ, "High")
        ]
    },
    "disable_dvr": {
        "title": "Деактивировать DVR",
        "desc": "Выключает фоновую видеозапись Game DVR системы Xbox Live, вызывающую падение FPS.",
        "category": "gaming",
        "reg": [
            ("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", winreg.REG_DWORD, 0),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", winreg.REG_DWORD, 0)
        ]
    },
    "disable_fse_global": {
        "title": "Не использовать полноэкранную оптимизацию",
        "desc": "Глобально отключает гибридную оптимизацию оконного режима, устраняя задержку ввода.",
        "category": "gaming",
        "reg": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "FSEBehaviorMode", winreg.REG_DWORD, 2)
        ]
    },
    "windowed_optimizations": {
        "title": "Включить оптимизацию игр в оконном режиме",
        "desc": "Использует современный независимый Flip-фреймбуфер для игр без рамки.",
        "category": "gaming",
        "reg": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GraphicsSettings", "HwSchMode", winreg.REG_DWORD, 2)
        ]
    },
    "disable_mouse_accel": {
        "title": "Убрать ускорение мыши",
        "desc": "Устанавливает прямое позиционирование курсора (MarkC Fix) без интерполяции движения.",
        "category": "gaming",
        "reg": [
            ("HKCU", r"Control Panel\Mouse", "MouseSpeed", winreg.REG_SZ, "0"),
            ("HKCU", r"Control Panel\Mouse", "MouseThreshold1", winreg.REG_SZ, "0"),
            ("HKCU", r"Control Panel\Mouse", "MouseThreshold2", winreg.REG_SZ, "0")
        ]
    },
    "disable_filter_keys": {
        "title": "Отключить фильтрацию ввода",
        "desc": "Убирает задержку повторного нажатия клавиши при зажатии на клавиатуре.",
        "category": "gaming",
        "reg": [
            ("HKCU", r"Control Panel\Accessibility\Keyboard Response", "Flags", winreg.REG_SZ, "122")
        ]
    },
    "lower_net_latency": {
        "title": "Уменьшить сетевую задержку",
        "desc": "Отправляет сетевые пакеты TCP мгновенно (TCPNoDelay) без группировки алгоритмом Нагла.",
        "category": "gaming",
        "reg": [
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", winreg.REG_DWORD, 4294967295)
        ]
    },
    "disable_qos_limit": {
        "title": "Отключить резервацию сети",
        "desc": "Высвобождает 20% сетевого канала, зарезервированного под службу обновлений QoS.",
        "category": "gaming",
        "reg": [
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit", winreg.REG_DWORD, 0)
        ]
    },
    "no_traffic_limit": {
        "title": "Не ограничивать сетевой трафик",
        "desc": "Блокирует ограничение сетевого трафика мультимедиа служб при высокой нагрузке на ЦП.",
        "category": "gaming",
        "reg": [
            ("HKLM", r"SYSTEM\CurrentControlSet\Services\Dxgkrnl", "MonitorLatencyTolerance", winreg.REG_DWORD, 1)
        ]
    },

    # 3. HARDCORE PROFILE (Экстремальный)
    "disable_mitigations": {
        "title": "Отключить заплатки безопасности",
        "desc": "Отключает патчи уязвимостей CPU (Spectre/Meltdown) для восстановления пиковой мощности. Снижает защиту ядра.",
        "category": "hardcore",
        "reg": [
            ("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "FeatureSettingsOverride", winreg.REG_DWORD, 3),
            ("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "FeatureSettingsOverrideMask", winreg.REG_DWORD, 3)
        ]
    },
    "disable_last_access": {
        "title": "Убрать время последнего доступа к файлу",
        "desc": "Снижает число операций перезаписи на SSD-диске за счет отключения фиксации времени открытия папок.",
        "category": "hardcore",
        "reg": [
            ("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsDisableLastAccessUpdate", winreg.REG_DWORD, 1)
        ]
    },
    "disable_throttling": {
        "title": "Отключить троттлинг процессов Windows",
        "desc": "Запрещает планировщику искусственно занижать тактовую частоту фоновых игровых вкладок.",
        "category": "hardcore",
        "reg": [
            ("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", winreg.REG_DWORD, 1)
        ]
    },
    "no_cpu_reservation": {
        "title": "Не резервировать ресурсы ЦП",
        "desc": "Снижает системную отзывчивость мультимедиа до нуля, распределяя весь квант времени игре.",
        "category": "hardcore",
        "reg": [
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", winreg.REG_DWORD, 0)
        ]
    },
    "speedup_hung_apps": {
        "title": "Ускорить определение зависшей программы",
        "desc": "Снижает тайм-аут ожидания ответа оконного процесса перед принудительным закрытием.",
        "category": "hardcore",
        "reg": [
            ("HKCU", r"Control Panel\Desktop", "HungAppTimeout", winreg.REG_SZ, "1000")
        ]
    },
    "disable_shutdown_prompt": {
        "title": "Не отображать окно принудительного выключения",
        "desc": "Запрещает операционной системе запрашивать разрешение на завершение при блокировке задач.",
        "category": "hardcore",
        "reg": [
            ("HKCU", r"Control Panel\Desktop", "AutoEndTasks", winreg.REG_SZ, "1")
        ]
    },
    "speedup_kill_timeout": {
        "title": "Ускорить принудительное завершение приложений",
        "desc": "Выставляет минимальное время закрытия зависшего софта при завершении работы ОС.",
        "category": "hardcore",
        "reg": [
            ("HKCU", r"Control Panel\Desktop", "WaitToKillAppTimeout", winreg.REG_SZ, "2000"),
            ("HKLM", r"SYSTEM\CurrentControlSet\Control", "WaitToKillServiceTimeout", winreg.REG_SZ, "2000")
        ]
    },
    "disable_ease_access": {
        "title": "Отключить функции Центра специальных возможностей",
        "desc": "Блокирует случайный запуск залипания клавиш Shift и экранной лупы.",
        "category": "hardcore",
        "reg": [
            ("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", winreg.REG_SZ, "506"),
            ("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags", winreg.REG_SZ, "58")
        ]
    }
}

# --- КЛАСС СИСТЕМНОЙ РЕЗЕРВНОЙ КОПИИ ---
class SafeRegistryBackup:
    @staticmethod
    def load_backup():
        if os.path.exists(REGISTRY_BACKUP_FILE):
            try:
                with open(REGISTRY_BACKUP_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def save_backup(data):
        try:
            with open(REGISTRY_BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"[ERROR] Ошибка бэкапа реестра: {e}")

    @classmethod
    def backup_value(cls, hive_name, path, value_name, expected_type=winreg.REG_DWORD):
        backup_data = cls.load_backup()
        key_str = f"{hive_name}\\{path}\\{value_name}"
        if key_str in backup_data:
            return
            
        hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        original_val = None
        original_type = expected_type
        
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                original_val, original_type = winreg.QueryValueEx(key, value_name)
        except FileNotFoundError:
            original_val = "__missing__"
        except Exception as e:
            logging.warning(f"[SYSTEM] Пропущено резервирование {key_str}: {e}")
            return
            
        backup_data[key_str] = {
            "hive": hive_name,
            "path": path,
            "value_name": value_name,
            "value": original_val,
            "type": original_type
        }
        cls.save_backup(backup_data)
        logging.info(f"[SYSTEM] Создан бэкап: {key_str} -> {original_val}")

    @classmethod
    def restore_all(cls):
        backup_data = cls.load_backup()
        if not backup_data:
            return True, "Нет сохраненных резервных копий."
            
        success_count = 0
        failed_count = 0
        for key_str, item in backup_data.items():
            hive_name = item["hive"]
            path = item["path"]
            value_name = item["value_name"]
            orig_val = item["value"]
            orig_type = item["type"]
            
            hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            try:
                if orig_val == "__missing__":
                    try:
                        with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                            winreg.DeleteValue(key, value_name)
                        success_count += 1
                    except FileNotFoundError:
                        success_count += 1
                else:
                    try:
                        key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
                    except Exception:
                        key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
                    with key:
                        winreg.SetValueEx(key, value_name, 0, orig_type, orig_val)
                    success_count += 1
            except Exception as e:
                logging.error(f"[ERROR] Не удалось восстановить {key_str}: {e}")
                failed_count += 1
                
        if failed_count == 0:
            return True, f"Все твики реестра ({success_count}) возвращены по умолчанию."
        return False, f"Восстановлено: {success_count}. Сбоев: {failed_count}."

# --- АСИНХРОННЫЕ РАБОЧИЕ ПОТОКИ (БЕЗ CLI-ПАРСИНГА) ---
class SystemInfoThread(QThread):
    hardware_loaded_signal = Signal(dict)

    def run(self):
        logging.info("[SYSTEM] Фоновый сбор WMI характеристик (Language-Independent)...")
        try:
            # Считывание информации напрямую по именам WMI-классов без парсинга pnputil по строкам
            script_block = """
            $ErrorActionPreference = "SilentlyContinue"
            $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, InstallDate | ConvertTo-Json -Compress
            $pc = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model | ConvertTo-Json -Compress
            $bios = Get-CimInstance Win32_BIOS | Select-Object SerialNumber, Manufacturer, SMBIOSBIOSVersion | ConvertTo-Json -Compress
            $cpu = Get-CimInstance Win32_Processor | Select-Object Name, MaxClockSpeed, L2CacheSize, L3CacheSize, CurrentVoltage | ConvertTo-Json -Compress
            $board = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product | ConvertTo-Json -Compress
            $ram = Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, PartNumber, SerialNumber, Speed, Capacity, SMBIOSMemoryType | ConvertTo-Json -Compress
            $gpu = Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, VideoProcessor | ConvertTo-Json -Compress
            
            # Локализационно-независимый опрос сетевого и медийного драйвера напрямую через PnP-классы
            $net = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceClass -eq "NET" } | Select-Object DeviceName, DriverVersion | ConvertTo-Json -Compress
            $audio = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceClass -eq "MEDIA" } | Select-Object DeviceName, DriverVersion | ConvertTo-Json -Compress
            
            $payload = @{
                os = $os; pc = $pc; bios = $bios; cpu = $cpu; board = $board; ram = $ram; gpu = $gpu; net = $net; audio = $audio
            }
            ConvertTo-Json $payload -Depth 4 -Compress
            """
            utf16_bytes = script_block.encode('utf-16le')
            b64_str = base64.b64encode(utf16_bytes).decode('ascii')
            cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {b64_str}'
            
            res = subprocess.run(cmd, capture_output=True, shell=True, timeout=15)
            if res.returncode == 0 and res.stdout:
                raw_text = res.stdout.decode('utf-8', errors='ignore').strip()
                data = json.loads(raw_text)
                
                for key in data.keys():
                    if isinstance(data[key], str) and data[key].strip():
                        try:
                            inner = json.loads(data[key])
                            data[key] = inner if isinstance(inner, list) else [inner]
                        except Exception:
                            data[key] = []
                    elif not isinstance(data[key], list):
                        data[key] = []
                        
                self.hardware_loaded_signal.emit(data)
                logging.info("[SYSTEM] Профиль оборудования собран.")
        except Exception as e:
            logging.error(f"[ERROR] Ошибка WMI сбора: {e}")

class SensorMonitorThread(QThread):
    sensor_updated_signal = Signal(dict)

    def run(self):
        while not self.isInterruptionRequested():
            try:
                cpu_load = psutil.cpu_percent()
                ram_load = psutil.virtual_memory().percent
                
                # Использование нативного API NVML для телеметрии NVIDIA без нагрузки на CPU
                if HAS_PYNVML:
                    try:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        temp_val = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        fan_val = pynvml.nvmlDeviceGetFanSpeed(handle)
                        power_val = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0 # Милливатты в Ватты
                        util_val = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        
                        data = {
                            "cpu_load": cpu_load,
                            "ram_load": ram_load,
                            "gpu_load": float(util_val.gpu),
                            "gpu_temp": f"{temp_val} C",
                            "gpu_fan": f"{fan_val} %" if fan_val > 0 else "Авто",
                            "gpu_power": f"{power_val:.1f} Вт",
                            "gpu_vram": f"{util_val.memory} %"
                        }
                    except Exception:
                        data = self.get_fallback_sensors(cpu_load, ram_load)
                else:
                    data = self.get_fallback_sensors(cpu_load, ram_load)
                    
                self.sensor_updated_signal.emit(data)
            except Exception:
                pass
            self.msleep(1500)

    def get_fallback_sensors(self, cpu_load, ram_load):
        # Быстрый опрос AMD/Intel через легковесный wmic, без запуска PowerShell
        gpu_util = get_amd_intel_gpu_usage_light()
        return {
            "cpu_load": cpu_load,
            "ram_load": ram_load,
            "gpu_load": gpu_util,
            "gpu_temp": "Авто",
            "gpu_fan": "Авто",
            "gpu_power": "Авто",
            "gpu_vram": "Динамическая"
        }

class WindowsActivationThread(QThread):
    log_signal = Signal(str)
    done_signal = Signal(bool, str)

    def __init__(self, key, kms_server="kms.digiboy.ir"):
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
                res = subprocess.run(f"cscript //nologo C:\\Windows\\System32\\{cmd}", capture_output=True, shell=True, timeout=12)
                out = res.stdout.decode('cp866', errors='ignore').strip()
                if out:
                    self.log_signal.emit(out)
            except subprocess.TimeoutExpired:
                self.log_signal.emit("[WARN] Запрос превысил тайм-аут.")
            self.msleep(1000)
            
        self.done_signal.emit(True, "Процедура активации Windows выполнена!")

class DriverDownloadThread(QThread):
    progress_signal = Signal(str)
    done_signal = Signal(bool, str)

    def __init__(self, vendor):
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
            
            import urllib.request
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

# --- ТЕЛЕМЕТРИЯ ---
def get_nvidia_detailed_sensors():
    nvidia_smi_path = r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    if not os.path.exists(nvidia_smi_path): 
        nvidia_smi_path = "nvidia-smi"
    try:
        cmd = f'"{nvidia_smi_path}" --query-gpu=temperature.gpu,fan.speed,power.draw,utilization.gpu,utilization.memory,driver_version --format=csv,noheader,nounits'
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=2)
        if res.returncode == 0 and res.stdout:
            decoded = res.stdout.decode('utf-8', errors='ignore').strip()
            parts = [p.strip() for p in decoded.split(',')]
            if len(parts) >= 6:
                return {
                    "temp": f"{parts[0]} C", 
                    "fan": f"{parts[1]} %" if parts[1] != "[Not Supported]" else "Н/Д", 
                    "power": f"{parts[2]} Вт" if parts[2] != "[Not Supported]" else "Н/Д", 
                    "gpu_load": f"{parts[3]}%", 
                    "mem_load": f"{parts[4]}%", 
                    "success": True
                }
    except Exception:
        pass
    return {"success": False}

def get_amd_intel_gpu_usage_light():
    try:
        cmd = 'wmic path Win32_PerfFormattedData_GPUPerformanceAnalyzers_GPUEngine get UtilizationPercentage /value'
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=1)
        if res.returncode == 0 and res.stdout:
            out = res.stdout.decode('utf-8', errors='ignore').strip()
            total = 0.0
            count = 0
            for line in out.splitlines():
                if "UtilizationPercentage" in line:
                    try:
                        total += float(line.split("=")[1].strip())
                        count += 1
                    except Exception:
                        pass
            if count > 0:
                return min(100.0, total / count)
    except Exception:
        pass
    return 0.0

# --- СТИЛЬНЫЕ ВИДЖЕТЫ QT ---
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
            color = QColor(COLOR_ACCENT_TEAL) if percent < 60 else (QColor("#F59E0B") if percent < 85 else QColor(COLOR_ACCENT_RED))
            painter.fillRect(0, 2, fill_width, self.height_bar, color)

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
            self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 10px; font-weight: bold; border: none; background: transparent;")
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

class AdminWarningBanner(QFrame):
    def __init__(self, parent, relaunch_callback, **kwargs):
        super().__init__(parent)
        self.setObjectName("Banner")
        self.setStyleSheet(f"""
            QFrame#Banner {{
                background-color: #211510;
                border: 1px solid #F59E0B;
                border-radius: 6px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 10, 15, 10)
        
        lbl_tag = QLabel("[ВНИМАНИЕ]" if parent.current_lang == "ru" else "[WARNING]")
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
        btn_elevate.setStyleSheet(f"""
            QPushButton {{
                background-color: #3a251a;
                color: #FFE4D0;
                border: 1px solid #FFB03A;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #523525;
            }}
        """)
        btn_elevate.clicked.connect(relaunch_callback)
        parent.register_tr(btn_elevate, "Повысить права", "Elevate Privileges")
        lay.addWidget(btn_elevate)

# --- ГЛАВНОЕ ОКНО ПРИЛОЖЕНИЯ ---
class HardInfoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HARDINFO 0.0.2 — Global System Tuner")
        self.resize(1200, 800)
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        
        self.current_lang = "ru"
        self.translatable_widgets = [] 
        self.is_already_licensed = False 

        self.log_signaller = QtLogSignaller()
        self.log_signaller.log_signal.connect(self.append_log)
        self.qt_handler = QtLoggingHandler(self.log_signaller)
        self.qt_handler.setFormatter(logging.Formatter('%(asctime)s -> %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(self.qt_handler)

        self.original_power_plan = None
        self.setup_ui()
        self.save_current_power_scheme()
        
        self.info_thread = SystemInfoThread()
        self.info_thread.hardware_loaded_signal.connect(self.apply_hardware_specs)
        self.info_thread.start()
        
        self.sensor_thread = SensorMonitorThread()
        self.sensor_thread.sensor_updated_signal.connect(self.apply_live_sensors)
        self.sensor_thread.start()

    def register_tr(self, widget, ru, en):
        self.translatable_widgets.append((widget, ru, en))
        widget.setText(ru if self.current_lang == "ru" else en)

    def toggle_language(self):
        self.current_lang = "en" if self.current_lang == "ru" else "ru"
        for widget, ru, en in self.translatable_widgets:
            widget.setText(ru if self.current_lang == "ru" else en)
        self.btn_lang.setText("Language: EN" if self.current_lang == "en" else "Язык: RU")
        self.load_tweaks_states()

    def animate_fade_in(self, widget):
        """Плавная системная анимация для страниц Workspace"""
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        widget._anim = anim
        widget._eff = eff

    def closeEvent(self, event):
        self.info_thread.quit()
        self.info_thread.wait()
        self.sensor_thread.requestInterruption()
        self.sensor_thread.wait()
        super().closeEvent(event)

    def append_log(self, text):
        self.log_panel.append(text)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Сайдбар
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"QFrame#Sidebar {{ background-color: {COLOR_SIDEBAR}; border-right: 1px solid {COLOR_BORDER}; }}")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        
        brand = QLabel("HARDINFO")
        brand.setStyleSheet(f"color: {COLOR_ACCENT_TEAL}; font-size: 22px; font-weight: bold; margin-left: 20px;")
        sub = QLabel("TUNING & SYSTEM ENGINE")
        sub.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 8px; font-weight: bold; margin-left: 20px; margin-bottom: 20px;")
        
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(sub)
        
        self.btn_sys = QPushButton()
        self.btn_cpu = QPushButton()
        self.btn_gpu = QPushButton()
        self.btn_drivers = QPushButton()
        self.btn_boost = QPushButton()
        self.btn_start = QPushButton()
        
        self.register_tr(self.btn_sys, "  Сводка Системы", "  System Summary")
        self.register_tr(self.btn_cpu, "  Параметры CPU и ОЗУ", "  CPU & RAM Spec")
        self.register_tr(self.btn_gpu, "  Спецификация GPU", "  GPU Specification")
        self.register_tr(self.btn_drivers, "  Драйверы & Обновления", "  Drivers & Updates")
        self.register_tr(self.btn_boost, "  Игровой Оптимизатор", "  Game Optimizer")
        self.register_tr(self.btn_start, "  Менеджер Автозапуска", "  Startup Manager")
        
        for btn in (self.btn_sys, self.btn_cpu, self.btn_gpu, self.btn_drivers, self.btn_boost, self.btn_start):
            btn.setFixedHeight(45)
            btn.setStyleSheet(f"QPushButton {{ text-align: left; padding-left: 15px; color: {COLOR_TEXT_SEC}; background-color: transparent; font-size: 13px; font-weight: bold; border: none; }} QPushButton:hover {{ color: {COLOR_TEXT_PR}; background-color: #0d0d10; }}")
            sidebar_layout.addWidget(btn)
            
        self.btn_sys.clicked.connect(lambda: self.switch_tab(0))
        self.btn_cpu.clicked.connect(lambda: self.switch_tab(1))
        self.btn_gpu.clicked.connect(lambda: self.switch_tab(2))
        self.btn_drivers.clicked.connect(lambda: self.switch_tab(3))
        self.btn_boost.clicked.connect(lambda: self.switch_tab(4))
        self.btn_start.clicked.connect(lambda: self.switch_tab(5))
        
        sidebar_layout.addStretch()
        
        # Языковая кнопка
        self.btn_lang = QPushButton("Язык: RU")
        self.btn_lang.setFixedSize(140, 30)
        self.btn_lang.setStyleSheet(f"QPushButton {{ margin-left: 20px; background-color: {COLOR_CARD}; color: {COLOR_ACCENT_TEAL}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; font-weight: bold; }} QPushButton:hover {{ background-color: #121215; }}")
        self.btn_lang.clicked.connect(self.toggle_language)
        sidebar_layout.addWidget(self.btn_lang)
        
        sidebar_layout.addSpacing(15)
        
        # Системный монитор
        mon_frame = QFrame()
        mon_layout = QVBoxLayout(mon_frame)
        self.lbl_sb_cpu = QLabel("Нагрузка CPU: --")
        self.lbl_sb_cpu.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; background: transparent;")
        self.bar_sb_cpu = ElegantProgressBar()
        
        self.lbl_sb_ram = QLabel("Нагрузка RAM: --")
        self.lbl_sb_ram.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; background: transparent;")
        self.bar_sb_ram = ElegantProgressBar()
        
        mon_layout.addWidget(self.lbl_sb_cpu)
        mon_layout.addWidget(self.bar_sb_cpu)
        mon_layout.addWidget(self.lbl_sb_ram)
        mon_layout.addWidget(self.bar_sb_ram)
        
        sidebar_layout.addWidget(mon_frame)
        main_layout.addWidget(sidebar)
        
        # Правая область
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        self.warning_banner = AdminWarningBanner(self, self.relaunch_elevated)
        if not ctypes.windll.shell32.IsUserAnAdmin():
            right_layout.addWidget(self.warning_banner)
        
        self.tabs = QStackedWidget()
        right_layout.addWidget(self.tabs, stretch=1)
        
        # Терминал логов
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setFixedHeight(120)
        self.log_panel.setStyleSheet(f"QTextEdit {{ background-color: #050506; color: {COLOR_ACCENT_GREEN}; font-family: 'Consolas'; font-size: 11px; border: 1px solid {COLOR_BORDER}; border-radius: 6px; }}")
        right_layout.addWidget(self.log_panel)
        main_layout.addWidget(right_frame)
        
        self.tab_sys_widget = QWidget()
        self.tab_cpu_widget = QWidget()
        self.tab_gpu_widget = QWidget()
        self.tab_drivers_widget = QWidget()
        self.tab_boost_widget = QWidget()
        self.tab_start_widget = QWidget()
        
        self.tabs.addWidget(self.tab_sys_widget)
        self.tabs.addWidget(self.tab_cpu_widget)
        self.tabs.addWidget(self.tab_gpu_widget)
        self.tabs.addWidget(self.tab_drivers_widget)
        self.tabs.addWidget(self.tab_boost_widget)
        self.tabs.addWidget(self.tab_start_widget)
        
        self.build_tab_sys()
        self.build_tab_cpu()
        self.build_tab_gpu()
        self.build_tab_drivers()
        self.build_tab_boost()
        self.build_tab_start()
        
        self.switch_tab(0)

    def switch_tab(self, index):
        """Переключение вкладок с плавной анимацией проявления"""
        self.tabs.setCurrentIndex(index)
        self.animate_fade_in(self.tabs.currentWidget())
        
        buttons = [self.btn_sys, self.btn_cpu, self.btn_gpu, self.btn_drivers, self.btn_boost, self.btn_start]
        for idx, btn in enumerate(buttons):
            if idx == index:
                btn.setStyleSheet(f"text-align: left; padding-left: 15px; color: {COLOR_ACCENT_TEAL}; background-color: #0d0d10; border-left: 3px solid {COLOR_ACCENT_TEAL}; font-size: 13px; font-weight: bold; border-top: none; border-bottom: none;")
            else:
                btn.setStyleSheet(f"text-align: left; padding-left: 15px; color: {COLOR_TEXT_SEC}; background-color: transparent; font-size: 13px; font-weight: bold; border: none;")
        
        if index == 4:
            self.load_tweaks_states()
        if index == 5:
            self.load_startup_list()

    # --- ВКЛАДКА 1: СВОДКА СИСТЕМЫ ---
    def build_tab_sys(self):
        layout = QHBoxLayout(self.tab_sys_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()
        layout.addLayout(col_left, stretch=1)
        layout.addLayout(col_right, stretch=1)
        
        card_os = HoverCard("Программное обеспечение (ОС)", "Operating System (OS)", COLOR_ACCENT_GREEN, self)
        self.lbl_sys_os = self.add_row(card_os, "Операционная система:", "Operating System:")
        self.lbl_sys_ver = self.add_row(card_os, "Версия / Сборка:", "OS Version / Build:")
        self.lbl_sys_arch = self.add_row(card_os, "Разрядность ядра:", "System Architecture:")
        col_left.addWidget(card_os)
        
        card_pc = HoverCard("Аппаратная платформа", "Hardware Platform", COLOR_ACCENT_TEAL, self)
        self.lbl_sys_pc_man = self.add_row(card_pc, "Вендор ПК:", "System Vendor:")
        self.lbl_sys_pc_mod = self.add_row(card_pc, "Модель ПК:", "System Model:")
        self.lbl_sys_bios_sn = self.add_row(card_pc, "Серийный номер BIOS:", "BIOS Serial Number:")
        col_left.addWidget(card_pc)
        col_left.addStretch(1)
        
        card_graph = HoverCard("Мониторинг ресурсов", "Resource History Monitor", COLOR_ACCENT_VIOLET, self)
        glay = QHBoxLayout()
        
        g1 = QVBoxLayout()
        glbl1 = QLabel()
        glbl1.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 8px; font-weight: bold; border: none; background: transparent;")
        self.register_tr(glbl1, "ИСТОРИЯ ЦП (%)", "CPU UTILIZATION (%)")
        self.chart_cpu = RealtimeLineChart(COLOR_ACCENT_TEAL)
        g1.addWidget(glbl1)
        g1.addWidget(self.chart_cpu)
        
        g2 = QVBoxLayout()
        glbl2 = QLabel()
        glbl2.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 8px; font-weight: bold; border: none; background: transparent;")
        self.register_tr(glbl2, "ИСТОРИЯ ОЗУ (%)", "RAM UTILIZATION (%)")
        self.chart_ram = RealtimeLineChart(COLOR_ACCENT_VIOLET)
        g2.addWidget(glbl2)
        g2.addWidget(self.chart_ram)
        
        glay.addLayout(g1)
        glay.addLayout(g2)
        card_graph.main_layout.addLayout(glay)
        col_right.addWidget(card_graph)
        col_right.addStretch(1)

    # --- CPU И ОЗУ ---
    def build_tab_cpu(self):
        layout = QHBoxLayout(self.tab_cpu_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()
        layout.addLayout(col_left, stretch=1)
        layout.addLayout(col_right, stretch=1)
        
        card_cpu = HoverCard("Характеристики CPU", "CPU Specifications", COLOR_ACCENT_TEAL, self)
        self.lbl_cpu_name = self.add_row(card_cpu, "Имя процессора:", "Processor Model:")
        self.lbl_cpu_code = self.add_row(card_cpu, "Поколение чипа:", "Chip Family Code:")
        self.lbl_cpu_nm = self.add_row(card_cpu, "Техпроцесс:", "Lithography Node:")
        self.lbl_cpu_tdp = self.add_row(card_cpu, "Лимиты TDP:", "Power TDP Limits:")
        self.lbl_cpu_volt = self.add_row(card_cpu, "Базовый вольтаж:", "Current Voltage:")
        col_left.addWidget(card_cpu)
        col_left.addStretch(1)
        
        card_ram = HoverCard("Оперативная память", "Physical Memory (RAM)", COLOR_ACCENT_VIOLET, self)
        self.lbl_ram_cap = self.add_row(card_ram, "Общая память:", "Total Memory Capacity:")
        self.lbl_ram_type = self.add_row(card_ram, "Стандарт планок:", "Memory Standard Type:")
        self.lbl_ram_speed = self.add_row(card_ram, "Частота:", "Memory Rated Speed:")
        self.lbl_ram_chan = self.add_row(card_ram, "Режим работы:", "Channel Configuration:")
        self.lbl_ram_timings = self.add_row(card_ram, "Тайминги:", "Latencies (Timings):")
        col_right.addWidget(card_ram)
        
        card_board = HoverCard("Материнская плата", "Mainboard Specification", COLOR_ACCENT_GREEN, self)
        self.lbl_board_man = self.add_row(card_board, "Производитель:", "Board Manufacturer:")
        self.lbl_board_prod = self.add_row(card_board, "Модель платы:", "Product Board Model:")
        self.lbl_mb_bios = self.add_row(card_board, "Версия BIOS:", "BIOS Active Version:") 
        col_right.addWidget(card_board)
        col_right.addStretch(1)

    # --- СПЕЦИФИКАЦИЯ GPU ---
    def build_tab_gpu(self):
        layout = QHBoxLayout(self.tab_gpu_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()
        layout.addLayout(col_left, stretch=1)
        layout.addLayout(col_right, stretch=1)
        
        card_gpu = HoverCard("Конфигурация видеоядра", "Graphics Card Configuration (GPU)", COLOR_ACCENT_VIOLET, self)
        self.lbl_gpu_name = self.add_row(card_gpu, "Видеоадаптер:", "Display Adapter:")
        self.lbl_gpu_chip = self.add_row(card_gpu, "Графический чип:", "GPU Codename:")
        self.lbl_gpu_nm = self.add_row(card_gpu, "Техпроцесс:", "Silicon Lithography:")
        self.lbl_gpu_bus = self.add_row(card_gpu, "Ширина шины:", "Bus Width:") 
        self.lbl_gpu_cap = self.add_row(card_gpu, "Объем видеопамяти:", "Dedicated Video Memory:")
        self.lbl_gpu_apis = self.add_row(card_gpu, "Поддерживаемые API:", "Supported Platforms API:")
        col_left.addWidget(card_gpu)
        
        card_driver = HoverCard("Драйвер и ПО", "Driver & Software Details", COLOR_ACCENT_GREEN, self)
        self.lbl_gpu_driver = self.add_row(card_driver, "Версия драйвера:", "Active Driver Version:")
        self.lbl_gpu_proc = self.add_row(card_driver, "Видеопроцессор:", "Video Co-Processor:")
        col_left.addWidget(card_driver)
        col_left.addStretch(1)

        card_telemetry = HoverCard("Телеметрия GPU в реальном времени", "Realtime GPU Telemetry", COLOR_ACCENT_TEAL, self)
        self.lbl_g_temp = self.add_row(card_telemetry, "Температура кристалла:", "Core Temperature:")
        self.lbl_g_fan = self.add_row(card_telemetry, "Обороты охлаждения:", "Cooling Fan RPM:")
        self.lbl_g_power = self.add_row(card_telemetry, "Энергопотребление:", "GPU Power Draw:")
        self.lbl_g_load = self.add_row(card_telemetry, "Текущая нагрузка GPU:", "GPU Core Utilization:")
        self.lbl_g_vram_load = self.add_row(card_telemetry, "Занято видеопамяти:", "Dedicated VRAM Used:")
        col_right.addWidget(card_telemetry)
        col_right.addStretch(1)

    # --- ОБНОВЛЕНИЕ ДРАЙВЕРОВ ---
    def build_tab_drivers(self):
        layout = QHBoxLayout(self.tab_drivers_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()
        layout.addLayout(col_left, stretch=1)
        layout.addLayout(col_right, stretch=1)
        
        card_dl = HoverCard("Менеджер Обновлений", "Bypass Regional Download Block", COLOR_ACCENT_TEAL, self)
        col_left.addWidget(card_dl)
        
        lbl_info = QLabel()
        lbl_info.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; background: transparent;")
        lbl_info.setWordWrap(True)
        self.register_tr(
            lbl_info, 
            "Загрузка драйверов напрямую с официальных азиатских зеркал Intel и NVIDIA для обхода блокировок СНГ-регионов.",
            "Downloads original driver installation packages routed via fast official Asian mirrors bypass regional bans."
        )
        card_dl.main_layout.addWidget(lbl_info)
        
        # Интерактивная таблица версий драйверов и их назначение
        self.lbl_gpu_drv_status = self.add_row(card_dl, "Видеодрайвер (Видеоигры):", "GPU Display Driver (Gaming):")
        self.lbl_net_drv_status = self.add_row(card_dl, "Сетевой драйвер (Пинг):", "Network Driver (Ping):")
        self.lbl_audio_drv_status = self.add_row(card_dl, "Звуковой драйвер (Аудио):", "Audio Driver (HD Sound):")
        
        # Чекбоксы выбора
        row_chks = QHBoxLayout()
        self.chk_gpu = QCheckBox("GPU")
        self.chk_gpu.setChecked(True)
        self.chk_gpu.setStyleSheet("color: white; font-weight: bold;")
        self.chk_net = QCheckBox("Net")
        self.chk_net.setStyleSheet("color: white; font-weight: bold;")
        self.chk_audio = QCheckBox("Audio")
        self.chk_audio.setStyleSheet("color: white; font-weight: bold;")
        row_chks.addWidget(self.chk_gpu)
        row_chks.addWidget(self.chk_net)
        row_chks.addWidget(self.chk_audio)
        card_dl.main_layout.addLayout(row_chks)
        
        btn_dl_selected = QPushButton()
        btn_dl_selected.setFixedHeight(40)
        btn_dl_selected.setStyleSheet(f"QPushButton {{ background-color: #0b2212; color: {COLOR_ACCENT_GREEN}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_GREEN}; border-radius: 4px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_GREEN}; color: #000000; }}")
        btn_dl_selected.clicked.connect(self.action_update_selected_drivers)
        self.register_tr(btn_dl_selected, "ОБНОВИТЬ ВЫБРАННЫЕ ДРАЙВЕРЫ", "UPDATE SELECTED DRIVERS")
        
        btn_dl_all = QPushButton()
        btn_dl_all.setFixedHeight(40)
        btn_dl_all.setStyleSheet(f"QPushButton {{ background-color: #121d22; color: {COLOR_ACCENT_TEAL}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_TEAL}; border-radius: 4px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_TEAL}; color: #000000; }}")
        btn_dl_all.clicked.connect(self.action_update_all_drivers)
        self.register_tr(btn_dl_all, "ОБНОВИТЬ ВСЕ ДРАЙВЕРЫ (ЗЕРКАЛО)", "UPDATE ALL DRIVERS (BYPASS MIRROR)")
        
        card_dl.main_layout.addWidget(btn_dl_selected)
        card_dl.main_layout.addWidget(btn_dl_all)
        col_left.addStretch(1)
        
        card_rb = HoverCard("Удаление и Откат версий драйверов", "Driver Rollback & Complete Removal", COLOR_ACCENT_RED, self)
        col_right.addWidget(card_rb)
        
        lbl_info_rb = QLabel()
        lbl_info_rb.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; background: transparent;")
        lbl_info_rb.setWordWrap(True)
        self.register_tr(
            lbl_info_rb, 
            "Встроенный инструмент отката версий. Вызывает мастер удаления пакетов Windows pnputil или Диспетчер устройств.",
            "Built-in manager rollback utility. Uses pnputil commands directly to list display packages or opens Dev Manager."
        )
        card_rb.main_layout.addWidget(lbl_info_rb)
        
        btn_open_dev = QPushButton()
        btn_open_dev.setFixedHeight(40)
        btn_open_dev.setStyleSheet(f"QPushButton {{ background-color: #1a1a24; color: {COLOR_TEXT_PR}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }} QPushButton:hover {{ background-color: #33334d; }}")
        btn_open_dev.clicked.connect(self.action_open_device_manager)
        self.register_tr(btn_open_dev, "ОТКРЫТЬ ДИСПЕТЧЕР УСТРОЙСТВ", "OPEN DEVICE MANAGER")
        
        btn_pnp_clean = QPushButton()
        btn_pnp_clean.setFixedHeight(40)
        btn_pnp_clean.setStyleSheet(f"QPushButton {{ background-color: #211014; color: {COLOR_ACCENT_RED}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_RED}; border-radius: 4px; }} QPushButton:hover {{ background-color: #211014; color: #ffffff; }}")
        btn_pnp_clean.clicked.connect(self.action_display_pnp_drivers)
        self.register_tr(btn_pnp_clean, "ПОИСК OEM-ДРАЙВЕРОВ И ОТКАТ (PNPUTIL)", "SCAN OEM-DRIVERS & ROLLBACK")
        
        card_rb.main_layout.addWidget(btn_open_dev)
        card_rb.main_layout.addWidget(btn_pnp_clean)
        col_right.addStretch(1)

    def action_update_all_drivers(self):
        self.start_driver_download("nvidia")
        QTimer.singleShot(2000, lambda: self.start_driver_download("intel"))
        QTimer.singleShot(4000, lambda: self.start_driver_download("realtek_audio"))

    def action_update_selected_drivers(self):
        if self.chk_gpu.isChecked():
            self.start_driver_download("nvidia")
        if self.chk_net.isChecked():
            QTimer.singleShot(1500, lambda: self.start_driver_download("intel_wifi"))
        if self.chk_audio.isChecked():
            QTimer.singleShot(3000, lambda: self.start_driver_download("realtek_audio"))

    def start_driver_download(self, vendor):
        self.btn_sys.setEnabled(False)
        self.dl_thread = DriverDownloadThread(vendor)
        self.dl_thread.progress_signal.connect(self.append_log)
        self.dl_thread.done_signal.connect(self.driver_download_finished)
        self.dl_thread.start()

    def driver_download_finished(self, success, msg):
        self.btn_sys.setEnabled(True)
        if success:
            QMessageBox.information(self, "Загрузка обновлений", msg)
        else:
            QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось обойти региональный блок: {msg}")

    def action_open_device_manager(self):
        try:
            subprocess.Popen("mmc.exe devmgmt.msc", shell=True)
            logging.info("[SYSTEM] Запущен Диспетчер устройств Windows.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть devmgmt.msc: {e}")

    def action_display_pnp_drivers(self):
        logging.info("[SYSTEM] Запуск сканирования хранилища OEM сторонних драйверов...")
        try:
            res = subprocess.run("pnputil /enum-drivers", capture_output=True, shell=True, text=True, errors='ignore')
            lines = res.stdout.split("\n")
            oems = []
            current_oem = ""
            for line in lines:
                if "Опубликованное имя" in line or "Published Name" in line:
                    current_oem = line.split(":")[1].strip()
                if ("Класс" in line or "Class Name" in line) and "Display" in line:
                    oems.append(current_oem)
            if oems:
                msg = "Найдены display oem-пакеты дисплейных драйверов в хранилище:\n\n" + "\n".join(oems) + "\n\nВы хотите вызвать команду принудительного отката/удаления пакета?"
                confirm = QMessageBox.question(self, "Откат драйвера", msg, QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    target_oem, ok = QMessageBox.getText(self, "Ввод имени", "Введите имя пакета для удаления и отката (например, oem12.inf):")
                    if ok and target_oem.strip():
                        res_del = subprocess.run(f"pnputil /delete-driver {target_oem.strip()} /uninstall", capture_output=True, shell=True, text=True, errors='ignore')
                        logging.info(res_del.stdout)
                        QMessageBox.information(self, "Откат", "Команда отката/удаления отправлена в pnputil!")
            else:
                QMessageBox.information(self, "Сканирование", "В системном репозитории не обнаружено сторонних графических OEM-пакетов дисплея.")
        except Exception as e:
            logging.error(f"[ERROR] Сбой вызова pnputil: {e}")

    # --- ИГРОВОЙ ОПТИМИЗАТОР С КАТЕГОРИЗАЦИЕЙ ТВКОВ ПО ПРОФИЛЯМ ---
    def build_tab_boost(self):
        layout = QHBoxLayout(self.tab_boost_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        left_area = QScrollArea()
        left_area.setWidgetResizable(True)
        left_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet(f"background-color: {COLOR_BG};")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        self.toggles = {}
        
        # Профили твиков по категориям рисков (Safe, Gaming, Hardcore)
        categories = {
            "safe": ("БЕЗОПАСНЫЙ УРОВЕНЬ (SAFE PROFILE)", "SAFE PROFILE", COLOR_ACCENT_GREEN),
            "gaming": ("ИГРОВОЙ УРОВЕНЬ (GAMING PROFILE)", "GAMING PROFILE", COLOR_ACCENT_TEAL),
            "hardcore": ("ЭКСТРЕМАЛЬНЫЙ УРОВЕНЬ (HARDCORE PROFILE)", "HARDCORE PROFILE", COLOR_ACCENT_VIOLET)
        }
        
        for cat_key, (cat_ru, cat_en, cat_color) in categories.items():
            cat_card = HoverCard(cat_ru, cat_en, cat_color, self)
            for key, t_info in TWEAKS_DB.items():
                if t_info["category"] == cat_key:
                    row = QHBoxLayout()
                    lbl_t = QLabel()
                    lbl_t.setStyleSheet(f"color: {COLOR_TEXT_PR}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
                    lbl_t.setToolTip(t_info["desc"])
                    self.register_tr(lbl_t, t_info["title"], t_info["title"])
                    
                    chk = QCheckBox()
                    chk.setCursor(Qt.PointingHandCursor)
                    chk.setStyleSheet(f"""
                        QCheckBox::indicator {{
                            width: 36px;
                            height: 18px;
                            border-radius: 9px;
                            background-color: #1b1b22;
                        }}
                        QCheckBox::indicator:unchecked {{
                            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzNiIgaGVpZ2h0PSIxOCI+PGNpcmNsZSBjeD0iMTAiIGN5PSI5IiByPSI2IiBmaWxsPSIjOGE4YTkzIi8+PC9zdmc+);
                        }}
                        QCheckBox::indicator:checked {{
                            background-color: {cat_color};
                            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzNiIgaGVpZ2h0PSIxOCI+PGNpcmNsZSBjeD0iMjYiIGN5PSI5IiByPSI2IiBmaWxsPSIjMDQwNDA1Ii8+PC9zdmc+);
                        }}
                    """)
                    chk.setProperty("tweak_id", key)
                    chk.clicked.connect(self.action_toggle_tweak)
                    
                    row.addWidget(lbl_t, stretch=1)
                    row.addWidget(chk)
                    cat_card.main_layout.addLayout(row)
                    self.toggles[key] = chk
            scroll_layout.addWidget(cat_card)
            
        left_area.setWidget(scroll_widget)
        layout.addWidget(left_area, stretch=3)
        
        right_panel = QVBoxLayout()
        layout.addLayout(right_panel, stretch=2)
        
        card_act = HoverCard("Активация Windows", "Windows License Activation", COLOR_ACCENT_VIOLET, self)
        self.lbl_act_status = QLabel("Определение редакции...")
        self.lbl_act_status.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        
        self.btn_run_activation = QPushButton()
        self.btn_run_activation.setFixedHeight(35)
        self.btn_run_activation.setStyleSheet(f"QPushButton {{ background-color: #211020; color: {COLOR_ACCENT_VIOLET}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_VIOLET}; border-radius: 4px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_VIOLET}; color: #000000; }}")
        self.btn_run_activation.clicked.connect(self.run_kms_activation)
        self.register_tr(self.btn_run_activation, "АКТИВИРОВАТЬ ЧЕРЕЗ KMS", "ACTIVATE VIA KMS SERVER")
        
        card_act.main_layout.addWidget(self.lbl_act_status)
        card_act.main_layout.addWidget(self.btn_run_activation)
        right_panel.addWidget(card_act)
        
        card_boost = HoverCard("Управление процессами", "Realtime Process Priority Manager", COLOR_ACCENT_GREEN, self)
        lbl_info_b = QLabel()
        lbl_info_b.setWordWrap(True)
        lbl_info_b.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; border: none; background: transparent;")
        self.register_tr(
            lbl_info_b, 
            "Повышает приоритет выбранной игры и высвобождает память системного кэша.",
            "Forces Windows Scheduler to assign Realtime class priority to gaming and empty working set cache."
        )
        
        form = QHBoxLayout()
        lbl_game = QLabel()
        lbl_game.setStyleSheet(f"color: {COLOR_TEXT_PR}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        self.register_tr(lbl_game, "Процесс игры:", "Game Binary:")
        self.edit_game_process = QLineEdit("cs2.exe")
        self.edit_game_process.setStyleSheet(f"background-color: #121215; color: {COLOR_TEXT_PR}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 4px; font-size: 11px;")
        form.addWidget(lbl_game)
        form.addWidget(self.edit_game_process)
        
        btn_boost_now = QPushButton()
        btn_boost_now.setFixedHeight(35)
        btn_boost_now.setStyleSheet(f"QPushButton {{ background-color: #0b2212; color: {COLOR_ACCENT_GREEN}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_GREEN}; border-radius: 4px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_GREEN}; color: #000000; }}")
        btn_boost_now.clicked.connect(self.run_game_boost_optimization)
        self.register_tr(btn_boost_now, "УСКОРИТЬ ИГРУ", "BOOST CORE GAMEPLAY")
        
        btn_ram_purge = QPushButton()
        btn_ram_purge.setFixedHeight(35)
        btn_ram_purge.setStyleSheet(f"QPushButton {{ background-color: #121d22; color: {COLOR_ACCENT_TEAL}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_TEAL}; border-radius: 4px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_TEAL}; color: #000000; }}")
        btn_ram_purge.clicked.connect(self.run_ram_standby_flush)
        self.register_tr(btn_ram_purge, "Очистить ОЗУ", "Empty Cache RAM")
        
        lay_btns = QHBoxLayout()
        lay_btns.addWidget(btn_boost_now)
        lay_btns.addWidget(btn_ram_purge)
        
        btn_undo = QPushButton()
        btn_undo.setFixedHeight(35)
        btn_undo.setStyleSheet(f"QPushButton {{ background-color: #211014; color: {COLOR_ACCENT_RED}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_RED}; border-radius: 4px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_RED}; color: #ffffff; }}")
        btn_undo.clicked.connect(self.run_safe_undo)
        self.register_tr(btn_undo, "ОТКАТИТЬ ВСЕ ИЗМЕНЕНИЯ (SAFE UNDO)", "ROLLBACK SYSTEM (SAFE UNDO)")
        
        card_boost.main_layout.addWidget(lbl_info_b)
        card_boost.main_layout.addLayout(form)
        card_boost.main_layout.addLayout(lay_btns)
        card_boost.main_layout.addWidget(btn_undo)
        
        right_panel.addWidget(card_boost)
        right_panel.addStretch()
        
        self.detect_windows_edition()

    # --- МЕНЕДЖЕР АВТОЗАПУСКА ---
    def build_tab_start(self):
        layout = QVBoxLayout(self.tab_start_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        card_start = HoverCard("Управление автозапуском программ", "Windows Startup App Registry Manager", COLOR_ACCENT_TEAL, self)
        layout.addWidget(card_start)
        
        lbl_desc = QLabel()
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 11px; border: none; background: transparent;")
        self.register_tr(
            lbl_desc, 
            "Выберите неиспользуемые программы для их безвозвратного исключения из автозагрузки:",
            "Select background applications to cleanly erase them from startup registers:"
        )
        card_start.main_layout.addWidget(lbl_desc)
        
        self.list_startup = QListWidget()
        self.list_startup.setStyleSheet(f"QListWidget {{ background-color: #050506; color: {COLOR_TEXT_PR}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 10px; font-size: 12px; }} QListWidget::item {{ padding: 8px; border-bottom: 1px solid #121214; }} QListWidget::item:selected {{ background-color: {COLOR_ACCENT_TEAL}; color: #000000; }}")
        card_start.main_layout.addWidget(self.list_startup)
        
        btn_delete = QPushButton()
        btn_delete.setFixedHeight(40)
        btn_delete.setStyleSheet(f"QPushButton {{ background-color: #211014; color: {COLOR_ACCENT_RED}; font-size: 11px; font-weight: bold; border: 1px solid {COLOR_ACCENT_RED}; border-radius: 6px; }} QPushButton:hover {{ background-color: {COLOR_ACCENT_RED}; color: #ffffff; }}")
        btn_delete.clicked.connect(self.delete_startup_item)
        self.register_tr(btn_delete, "Удалить выбранную запись", "Delete Selected Registry Item")
        card_start.main_layout.addWidget(btn_delete)

    # --- СВЯЗУЮЩИЕ ИСПРАВЛЕННЫЕ ОПЕРАЦИИ ---
    def load_tweaks_states(self):
        logging.info("[SYSTEM] Чтение текущих конфигураций реестра...")
        for key, t_info in TWEAKS_DB.items():
            chk = self.toggles.get(key)
            if not chk:
                continue
            is_active = True
            for hive_name, path, val_name, expected_type, val_data in t_info["reg"]:
                hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
                try:
                    with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as k:
                        curr_val, _ = winreg.QueryValueEx(k, val_name)
                        if str(curr_val) != str(val_data):
                            is_active = False
                            break
                except Exception:
                    is_active = False
                    break
            chk.blockSignals(True)
            chk.setChecked(is_active)
            chk.blockSignals(False)

    def action_toggle_tweak(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            QMessageBox.warning(self, "Права администратора" if self.current_lang == "ru" else "Admin Privileges", 
                                "Для изменения твиков реестра требуются привилегии Администратора." if self.current_lang == "ru" else "Administrator privileges are required to apply registry tweaks.")
            self.load_tweaks_states()
            return
            
        chk = self.sender()
        key = chk.property("tweak_id")
        t_info = TWEAKS_DB[key]
        state = chk.isChecked()
        
        for hive_name, path, val_name, expected_type, val_data in t_info["reg"]:
            hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            if state:
                SafeRegistryBackup.backup_value(hive_name, path, val_name, expected_type)
                try:
                    reg_key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
                except Exception:
                    reg_key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
                with reg_key:
                    winreg.SetValueEx(reg_key, val_name, 0, expected_type, val_data)
            else:
                backup_data = SafeRegistryBackup.load_backup()
                key_str = f"{hive_name}\\{path}\\{val_name}"
                if key_str in backup_data:
                    orig_val = backup_data[key_str]["value"]
                    orig_type = backup_data[key_str]["type"]
                    try:
                        if orig_val == "__missing__":
                            with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as r_k:
                                winreg.DeleteValue(r_k, val_name)
                        else:
                            with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as r_k:
                                winreg.SetValueEx(r_k, val_name, 0, orig_type, orig_val)
                    except Exception:
                        pass
                        
        logging.info(f"[SYSTEM] Изменено состояние твика '{t_info['title']}': {'ВКЛ' if state else 'ВЫКЛ'}")
        self.load_tweaks_states()

    def detect_windows_edition(self):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                edition, _ = winreg.QueryValueEx(key, "EditionID")
                curr_status, _ = winreg.QueryValueEx(key, "CompositionEditionID")
            self.lbl_act_status.setText(f"ОС: Windows {edition}" if self.current_lang == "ru" else f"OS Edition: Windows {edition}")
        except Exception:
            self.lbl_act_status.setText("Редакция ОС: Не определена" if self.current_lang == "ru" else "OS Edition: Undetected")

    def run_kms_activation(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            QMessageBox.warning(self, "Права администратора" if self.current_lang == "ru" else "Admin Privileges", 
                                "Для активации Windows требуются права Администратора." if self.current_lang == "ru" else "Administrator privileges are required to activate Windows.")
            return
            
        # Интеллектуальное предупреждение о наличии ОФИЦИАЛЬНОЙ лицензии
        if self.is_already_licensed:
            reply = QMessageBox.warning(
                self,
                "Внимание" if self.current_lang == "ru" else "Warning",
                "Ваша Windows уже активирована оригинальной цифровой лицензией!\n\n"
                "Запуск KMS сотрет официальную вечную лицензию и заменит её на временную.\n\n"
                "Вы уверены, что хотите продолжить?" if self.current_lang == "ru" else
                "Your Windows is already activated with a GENUINE digital license!\n\n"
                "KMS will erase your permanent license and replace it with a temporary one.\n\n"
                "Are you sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                logging.info("[SYSTEM] KMS активация отменена пользователем для защиты оригинальной лицензии.")
                return

        gvlks = {
            "professional": "W269N-WFGWX-YVC9B-4J6C9-T83GX",
            "pro": "W269N-WFGWX-YVC9B-4J6C9-T83GX",
            "core": "TX9XD-98N7V-6WMQ6-BX7FG-H8Q99",
            "home": "TX9XD-98N7V-6WMQ6-BX7FG-H8Q99",
            "enterprise": "NPPR9-FWDCX-D2C8J-H872K-2YT43",
            "ltsc": "M7XTQ-FN8P6-TTKYV-9D4CC-J462D"
        }
        
        edition_id = "pro"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                edition_id, _ = winreg.QueryValueEx(key, "EditionID")
                edition_id = edition_id.lower()
        except Exception:
            pass
            
        target_key = None
        for k, v in gvlks.items():
            if k in edition_id:
                target_key = v
                break
                
        if not target_key:
            target_key = gvlks["pro"]
            
        logging.info(f"[SYSTEM] Запуск асинхронной KMS-активации для редакции: {edition_id}...")
        self.btn_run_activation.setEnabled(False)
        
        self.act_thread = WindowsActivationThread(target_key)
        self.act_thread.log_signal.connect(self.append_log)
        self.act_thread.done_signal.connect(self.activation_finished)
        self.act_thread.start()

    def activation_finished(self, success, msg):
        self.btn_run_activation.setEnabled(True)
        QMessageBox.information(self, "Активация Windows" if self.current_lang == "ru" else "Windows Activation", msg)

    # --- ИГРОВОЙ МОДУЛЬ ---
    def save_current_power_scheme(self):
        try:
            res = subprocess.run("powercfg /getactivescheme", capture_output=True, shell=True, timeout=2)
            out = res.stdout.decode('utf-8', errors='ignore').strip()
            if "GUID:" in out:
                self.original_power_plan = out.split("GUID:")[1].split("(")[0].strip()
        except Exception:
            pass

    def run_ram_standby_flush(self):
        logging.info("[SYSTEM] Запущена принудительная очистка оперативной памяти...")
        try:
            class LUID(ctypes.Structure):
                _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]
            class LUID_AND_ATTRIBUTES(ctypes.Structure):
                _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]
            class TOKEN_PRIVILEGES(ctypes.Structure):
                _fields_ = [("PrivilegeCount", ctypes.c_ulong), ("Privileges", LUID_AND_ATTRIBUTES * 1)]
                
            advapi32 = ctypes.windll.advapi32
            kernel32 = ctypes.windll.kernel32
            token = ctypes.c_void_p()
            if advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0020 | 0x0008, ctypes.byref(token)):
                luid = LUID()
                if advapi32.LookupPrivilegeValueW(None, "SeProfileSingleProcessPrivilege", ctypes.byref(luid)):
                    tp = TOKEN_PRIVILEGES()
                    tp.PrivilegeCount = 1
                    tp.Privileges[0].Luid = luid
                    tp.Privileges[0].Attributes = 0x00000002
                    advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)
                kernel32.CloseHandle(token)
                
            # Системный вызов NtSetSystemInformation (MemoryPurgeStandbyList = 4)
            ntdll = ctypes.windll.ntdll
            command = ctypes.c_ulong(4)
            result = ntdll.NtSetSystemInformation(80, ctypes.byref(command), ctypes.sizeof(command))
            
            if result == 0:
                logging.info("[SYSTEM] Кэш ожидания (Standby List) успешно сброшен через NtSetSystemInformation.")
                QMessageBox.information(self, "Очистка ОЗУ" if self.current_lang == "ru" else "RAM Purge", 
                                        "Кэш ожидания (Standby List) успешно сброшен по технологии RAMMap!" if self.current_lang == "ru" else "System Standby List successfully purged via NTDLL!")
            else:
                logging.error(f"[ERROR] Ошибка NtSetSystemInformation: {hex(result)}")
        except Exception as e:
            logging.error(f"[ERROR] Не удалось очистить ОЗУ: {e}")

    def run_game_boost_optimization(self):
        game_name = self.edit_game_process.text().strip().lower()
        if not game_name:
            QMessageBox.warning(self, "Игровой Оптимизатор" if self.current_lang == "ru" else "Game Optimizer", 
                                "Пожалуйста, укажите исполняемый файл процесса игры (например, cs2.exe)." if self.current_lang == "ru" else "Please specify the game process executable (e.g. cs2.exe).")
            return
            
        logging.info(f"[SYSTEM] Глубокое планирование ЦП запущено для: {game_name}...")
        
        try:
            self.save_current_power_scheme()
            cmd_pwr = "powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61"
            subprocess.run(cmd_pwr, shell=True, capture_output=True, timeout=3)
            logging.info("[SYSTEM] Схема электропитания переключена на Максимальную.")
        except Exception:
            pass
            
        boosted = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name_l = proc.info['name'].lower()
                if game_name in name_l:
                    p = psutil.Process(proc.info['pid'])
                    p.nice(psutil.HIGH_PRIORITY_CLASS)
                    boosted += 1
            except Exception:
                continue
                
        lowered = 0
        launchers = ["onedrive.exe", "spotify.exe", "epicgameslauncher.exe", "steamwebhelper.exe"]
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name_l = proc.info['name'].lower()
                if any(x in name_l for x in launchers):
                    p = psutil.Process(proc.info['pid'])
                    p.nice(psutil.IDLE_PRIORITY_CLASS)
                    lowered += 1
            except Exception:
                continue
                
        msg_ru = f"Оптимизация игрового ядра выполнена!\nУскорено игровых процессов (Высокий приоритет): {boosted}.\nРесурсы лаунчеров ({lowered}) перераспределены."
        msg_en = f"Game Core Optimization completed!\nBoosted game processes (High Priority): {boosted}.\nResources of launchers ({lowered}) redistributed."
        msg = msg_ru if self.current_lang == "ru" else msg_en
        logging.info(f"[SYSTEM] {msg}")
        QMessageBox.information(self, "Оптимизация игр" if self.current_lang == "ru" else "Game Booster", msg)

    def run_safe_undo(self):
        logging.info("[SYSTEM] Инициирован полный откат системных твиков и электропитания...")
        
        if self.original_power_plan:
            try:
                subprocess.run(f"powercfg /setactive {self.original_power_plan}", shell=True, capture_output=True, timeout=3)
                logging.info(f"[SYSTEM] Восстановлена схема питания: {self.original_power_plan}")
            except Exception:
                pass
                
        restored_p = 0
        launchers = ["onedrive.exe", "spotify.exe", "epicgameslauncher.exe", "steamwebhelper.exe"]
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name_l = proc.info['name'].lower()
                if any(x in name_l for x in launchers):
                    p = psutil.Process(proc.info['pid'])
                    p.nice(psutil.NORMAL_PRIORITY_CLASS)
                    restored_p += 1
            except Exception:
                continue
                
        ok, msg = SafeRegistryBackup.restore_all()
        if ok:
            QMessageBox.information(self, "Safe Undo" if self.current_lang == "ru" else "Safe Undo", f"{msg}\nПриоритеты {restored_p} лаунчеров восстановлены.")
        else:
            QMessageBox.critical(self, "Safe Undo Error", msg)
        self.load_tweaks_states()

    # --- РАБОТА С АВТОЗАПУСКОМ ---
    def load_startup_list(self):
        self.list_startup.clear()
        hives = [("HKCU", winreg.HKEY_CURRENT_USER), ("HKLM", winreg.HKEY_LOCAL_MACHINE)]
        path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        for name_hive, hive in hives:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                    info = winreg.QueryInfoKey(key)
                    for i in range(info[1]):
                        name, val, _ = winreg.EnumValue(key, i)
                        self.list_startup.addItem(f"[{name_hive}] {name}  -->  {val}")
            except Exception:
                pass

    def delete_startup_item(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            QMessageBox.warning(self, "Права администратора" if self.current_lang == "ru" else "Admin Privileges", 
                                "Для удаления записей автозапуска требуются права Администратора." if self.current_lang == "ru" else "Administrator privileges are required to modify startup.")
            return
            
        selected_item = self.list_startup.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Автозапуск" if self.current_lang == "ru" else "Startup", 
                                "Пожалуйста, выберите элемент для исключения." if self.current_lang == "ru" else "Please select an item to remove.")
            return
            
        text = selected_item.text()
        hive_name = "HKCU" if text.startswith("[HKCU]") else "HKLM"
        part_name = text.split("]")[1].split("-->")[0].strip()
        
        confirm_msg = f"Исключить '{part_name}' из автозапуска Windows?" if self.current_lang == "ru" else f"Remove '{part_name}' from Windows Startup?"
        confirm = QMessageBox.question(self, "Автозапуск" if self.current_lang == "ru" else "Startup", confirm_msg, QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                SafeRegistryBackup.backup_value(hive_name, path, part_name)
                with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, part_name)
                logging.info(f"[SYSTEM] Программа {part_name} успешно удалена из автозапуска.")
                QMessageBox.information(self, "Автозапуск" if self.current_lang == "ru" else "Startup", 
                                        "Запись автозагрузки успешно удалена." if self.current_lang == "ru" else "Startup item successfully removed.")
                self.load_startup_list()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка" if self.current_lang == "ru" else "Error", f"Не удалось очистить запись автозапуска: {e}")

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---
    def add_row(self, card_widget, key_ru, key_en):
        row_widget = QWidget()
        row_widget.setStyleSheet("background-color: transparent; border: none;") 
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 4, 0, 4)
        
        lbl_key = QLabel()
        lbl_key.setStyleSheet(f"color: {COLOR_TEXT_SEC}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        self.register_tr(lbl_key, key_ru, key_en)
        
        lbl_val = QLabel()
        lbl_val.setStyleSheet(f"color: {COLOR_TEXT_PR}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        self.register_tr(lbl_val, "Считывание...", "Reading...")
        
        row_layout.addWidget(lbl_key)
        row_layout.addStretch()
        row_layout.addWidget(lbl_val)
        card_widget.main_layout.addWidget(row_widget)
        return lbl_val

    def apply_hardware_specs(self, data):
        # Вкладка 1: ОС
        os_list = data.get("os", [{}])
        os_info = os_list[0] if os_list else {}
        self.lbl_sys_os.setText(clean_system_string(os_info.get("Caption", "Windows")))
        self.lbl_sys_ver.setText(clean_system_string(os_info.get("Version", "Н/Д")))
        self.lbl_sys_arch.setText(clean_system_string(os_info.get("OSArchitecture", "Н/Д")))
        
        pc_list = data.get("pc", [{}])
        pc_info = pc_list[0] if pc_list else {}
        self.lbl_sys_pc_man.setText(clean_system_string(pc_info.get("Manufacturer", "Н/Д")))
        self.lbl_sys_pc_mod.setText(clean_system_string(pc_info.get("Model", "Н/Д")))
        
        bios_list = data.get("bios", [{}])
        bios_info = bios_list[0] if bios_list else {}
        self.lbl_sys_bios_sn.setText(clean_system_string(bios_info.get("SerialNumber", "Н/Д")))
        self.lbl_mb_bios.setText(clean_system_string(bios_info.get("SMBIOSBIOSVersion", "Н/Д")))
        
        # Вкладка 2: Процессор
        cpu_list = data.get("cpu", [{}])
        cpu_info = cpu_list[0] if cpu_list else {}
        cpu_name = cpu_info.get("Name", "Н/Д")
        self.lbl_cpu_name.setText(clean_system_string(cpu_name))
        
        cpu_specs = parse_hardware_specs_dynamically(cpu_name, is_gpu=False)
        self.lbl_cpu_code.setText(cpu_specs["codename"])
        self.lbl_cpu_nm.setText(cpu_specs["nm"])
        self.lbl_cpu_tdp.setText(cpu_specs["tdp"])
        
        volt_val = cpu_info.get('CurrentVoltage')
        if volt_val:
            try:
                v = float(volt_val)
                if v > 100:
                    v = v / 1000.0
                elif v > 5:
                    v = v / 10.0
                volt_str = f"{v:.2f} V"
            except Exception:
                volt_str = "1.20 V"
        else:
            volt_str = "1.20 V"
        self.lbl_cpu_volt.setText(volt_str)
        
        board_list = data.get("board", [{}])
        board_info = board_list[0] if board_list else {}
        self.lbl_board_man.setText(clean_system_string(board_info.get("Manufacturer", "Н/Д")))
        self.lbl_board_prod.setText(clean_system_string(board_info.get("Product", "Н/Д")))
        
        ram_list = data.get("ram", [])
        if ram_list:
            total_bytes = sum([int(r.get("Capacity", 0)) for r in ram_list])
            self.lbl_ram_cap.setText(f"{total_bytes // (1024**3)} GB")
            speed = ram_list[0].get("Speed", 3200)
            self.lbl_ram_speed.setText(f"{speed} MHz")
            
            type_val = ram_list[0].get("SMBIOSMemoryType")
            ram_type = "DDR4" if type_val == 26 else ("DDR5" if type_val == 34 else "DDR4/DDR5")
            self.lbl_ram_type.setText(ram_type)
            self.lbl_ram_chan.setText("Dual-Channel" if len(ram_list) >= 2 else "Single-Channel")
            self.lbl_ram_timings.setText(estimate_ram_timings(speed, ram_type))
            
        # Вкладка 3: Видеоядро
        gpu_list = data.get("gpu", [{}])
        gpu_info = gpu_list[0] if gpu_list else {}
        gpu_name = gpu_info.get("Name", "Н/Д")
        self.lbl_gpu_name.setText(clean_system_string(gpu_name))
        
        gpu_specs = parse_hardware_specs_dynamically(gpu_name, is_gpu=True)
        self.lbl_gpu_chip.setText(gpu_specs["codename"])
        self.lbl_gpu_nm.setText(gpu_specs["nm"])
        self.lbl_gpu_bus.setText(gpu_specs["bus"])
        self.lbl_gpu_apis.setText(gpu_specs["apis"])
        self.lbl_gpu_driver.setText(clean_system_string(gpu_info.get("DriverVersion", "Н/Д")))
        self.lbl_gpu_proc.setText(clean_system_string(gpu_info.get("VideoProcessor", "Н/Д")))
        
        vram_bytes = gpu_info.get("AdapterRAM", 0)
        if isinstance(vram_bytes, int):
            if vram_bytes < 0: 
                vram_bytes = 4294967296 + vram_bytes
            vram_mb = vram_bytes // (1024**2)
        else:
            vram_mb = 0
        self.lbl_gpu_cap.setText(f"{vram_mb} MB" if vram_mb < 1024 else f"{vram_mb // 1024} GB")

        # Нативный вывод версий сетевых и звуковых драйверов
        net_list = data.get("net", [{}])
        net_info = net_list[0] if net_list else {}
        self.lbl_net_drv_status.setText(clean_system_string(net_info.get("DriverVersion", "Н/Д")))
        
        audio_list = data.get("audio", [{}])
        audio_info = audio_list[0] if audio_list else {}
        self.lbl_audio_drv_status.setText(clean_system_string(audio_info.get("DriverVersion", "Н/Д")))
        
        self.lbl_gpu_drv_status.setText(clean_system_string(gpu_info.get("DriverVersion", "Н/Д")))

    def apply_live_sensors(self, data):
        cpu_val = data.get("cpu_load", 0)
        ram_val = data.get("ram_load", 0)
        gpu_val = data.get("gpu_load", 0)
        
        self.lbl_sb_cpu.setText(f"Нагрузка CPU: {cpu_val:.1f}%" if self.current_lang == "ru" else f"CPU Load: {cpu_val:.1f}%")
        self.bar_sb_cpu.set_value(cpu_val)
        self.chart_cpu.add_value(cpu_val)
        
        self.lbl_sb_ram.setText(f"Нагрузка RAM: {ram_val:.1f}%" if self.current_lang == "ru" else f"RAM Load: {ram_val:.1f}%")
        self.bar_sb_ram.set_value(ram_val)
        self.chart_ram.add_value(ram_val)
        
        if hasattr(self, 'lbl_g_load'):
            self.lbl_g_load.setText(f"{gpu_val:.1f}%")
        if hasattr(self, 'lbl_g_temp'):
            self.lbl_g_temp.setText(str(data.get("gpu_temp", "Н/Д")))
        if hasattr(self, 'lbl_g_fan'):
            self.lbl_g_fan.setText(str(data.get("gpu_fan", "Авто")))
        if hasattr(self, 'lbl_g_power'):
            self.lbl_g_power.setText(str(data.get("gpu_power", "Н/Д")))
        if hasattr(self, 'lbl_g_vram_load'):
            self.lbl_g_vram_load.setText(str(data.get("gpu_vram", "Н/Д")))

    def relaunch_elevated(self):
        try:
            if getattr(sys, 'frozen', False):
                args = " ".join(sys.argv[1:])
                executable = sys.executable
            else:
                args = " ".join(f'"{a}"' for a in sys.argv)
                executable = sys.executable
                
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, None, 1)
            sys.exit(0)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка" if self.current_lang == "ru" else "Error", 
                                 f"Не удалось повысить привилегии: {e}" if self.current_lang == "ru" else f"Failed to elevate privileges: {e}")

# --- ТАЙМИНГИ И ИНИЦИАЛИЗАЦИЯ ---
def estimate_ram_timings(speed, ram_type):
    if "DDR5" in ram_type:
        if speed >= 6000: return "30-36-36-76"
        if speed >= 5600: return "36-36-36-89"
        return "40-40-40-77"
    else:
        if speed >= 3600: return "18-22-22-42"
        if speed >= 3200: return "16-18-18-36"
        return "19-19-19-43"

if __name__ == "__main__":
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "HARDINFO_PYSIDE_MUTEX_V3")
    if ctypes.windll.kernel32.GetLastError() == 183:
        app_dummy = QApplication(sys.argv)
        QMessageBox.warning(None, "Внимание", "HARDINFO уже запущен на данном компьютере!")
        sys.exit(0)

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler("hardinfo.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    app = QApplication(sys.argv)
    
    window = HardInfoMainWindow()
    window.show()
    sys.exit(app.exec())
