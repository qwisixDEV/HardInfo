import sys
import os
import platform
import subprocess
import json
import threading
import time
import tempfile
import socket
import ctypes
import logging
import tkinter as tk
import psutil
from tkinter import messagebox

APP_VERSION = "0.0.1"
# --- ДИАГНОСТИКА АВТОЗАГРУЗКИ (БЕЗ F-STRINGS) ---
def log_startup_debug():
    try:
        if "__compiled__" in dir() or getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        debug_file = os.path.join(base_dir, "startup_debug.log")
        with open(debug_file, "a", encoding="utf-8") as f:
            f.write("\n" + "="*60 + "\n")
            f.write("[" + time.strftime('%Y-%m-%d %H:%M:%S') + "] Запуск программы\n")
            f.write("  sys.executable: " + str(sys.executable) + "\n")
            f.write("  sys.argv: " + str(sys.argv) + "\n")
            f.write("  os.getcwd(): " + str(os.getcwd()) + "\n")
            f.write("  __compiled__: " + str("__compiled__" in dir()) + "\n")
            f.write("  sys.frozen: " + str(getattr(sys, 'frozen', False)) + "\n")
            has_startup = "--startup" in sys.argv
            has_silent = "--silent" in sys.argv
            f.write("  Аргументы: --startup=" + str(has_startup) + ", --silent=" + str(has_silent) + "\n")
    except Exception:
        pass

log_startup_debug()

# --- ФИКС РАБОЧЕЙ ДИРЕКТОРИИ ---
if "__compiled__" in dir() or getattr(sys, 'frozen', False):
    try:
        exe_dir = os.path.dirname(sys.executable)
        os.chdir(exe_dir)
    except Exception:
        pass

# --- НАСТРОЙКА СИСТЕМНОГО ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("hardinfo.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- УСТРАНЕНИЕ РАЗМЫТИЯ ШРИФТОВ НА 2K/4K МОНИТОРАХ ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- ЦВЕТОВАЯ ПАЛИТРА PITCH BLACK & NEON ---
COLOR_BG = "#000000"          # Глубокий черный фон
COLOR_SIDEBAR = "#050506"     # Сайдбар (темный обсидиан)
COLOR_CARD = "#0B0B0C"        # Фон карточек
COLOR_BORDER = "#141416"      # Тонкие темные границы карточек
COLOR_TEXT_PR = "#FFFFFF"     # Основной белый
COLOR_TEXT_SEC = "#7A7A82"    # Приглушенный серый
COLOR_ACCENT_TEAL = "#00FFCC" # Свечение Teal (ЦП / Сеть)
COLOR_ACCENT_VIOLET = "#D946EF"# Розовый неон (Видеокарта)
COLOR_ACCENT_GREEN = "#00FF66"# Зеленый неон (Система / Здоровье / Ок)
COLOR_ACCENT_RED = "#FF3366"  # Красный неон (Нагрузка / Внимание / Откат)

GPU_DATABASE = {
    "RTX 4090": {"chip": "AD102", "nm": "4 nm", "shaders": "16384", "tmus": "512", "rops": "176", "bus": "384-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 4080": {"chip": "AD103", "nm": "4 nm", "shaders": "9728", "tmus": "304", "rops": "112", "bus": "256-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 4070 Ti": {"chip": "AD104", "nm": "4 nm", "shaders": "7680", "tmus": "240", "rops": "80", "bus": "192-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 4070": {"chip": "AD104", "nm": "4 nm", "shaders": "5888", "tmus": "184", "rops": "64", "bus": "192-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 4060 Ti": {"chip": "AD106", "nm": "4 nm", "shaders": "4352", "tmus": "136", "rops": "48", "bus": "128-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 4060": {"chip": "AD107", "nm": "4 nm", "shaders": "3072", "tmus": "96", "rops": "48", "bus": "128-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 4050": {"chip": "AD107", "nm": "4 nm", "shaders": "2560", "tmus": "80", "rops": "48", "bus": "96-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 3090": {"chip": "GA102", "nm": "8 nm", "shaders": "10496", "tmus": "328", "rops": "112", "bus": "384-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 3080": {"chip": "GA102", "nm": "8 nm", "shaders": "8704", "tmus": "272", "rops": "96", "bus": "320-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 3070": {"chip": "GA104", "nm": "8 nm", "shaders": "5888", "tmus": "184", "rops": "96", "bus": "256-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 3060 Ti": {"chip": "GA104", "nm": "8 nm", "shaders": "4864", "tmus": "152", "rops": "80", "bus": "256-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 3060": {"chip": "GA106", "nm": "8 nm", "shaders": "3584", "tmus": "112", "rops": "48", "bus": "192-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "RTX 3050": {"chip": "GA106", "nm": "8 nm", "shaders": "2560", "tmus": "80", "rops": "32", "bus": "128-bit", "apis": "DX12.2, Vulkan, CUDA, OpenCL"},
    "GTX 1660": {"chip": "TU116", "nm": "12 nm", "shaders": "1408", "tmus": "88", "rops": "48", "bus": "192-bit", "apis": "DX12, Vulkan, CUDA, OpenCL"},
    "GTX 1650": {"chip": "TU117", "nm": "12 nm", "shaders": "896", "tmus": "56", "rops": "32", "bus": "128-bit", "apis": "DX12, Vulkan, CUDA, OpenCL"},
}

SUSPEND_LIST = [
    "chrome.exe", "msedge.exe", "browser.exe", "discord.exe", 
    "onedrive.exe", "spotify.exe", "epicgameslauncher.exe", 
    "origin.exe"
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except Exception:
        return False

def set_windows_exe_icon(root_window):
    try:
        hwnd = ctypes.windll.user32.GetParent(root_window.winfo_id())
        h_instance = ctypes.windll.kernel32.GetModuleHandleW(None)
        h_icon = ctypes.windll.user32.LoadIconW(h_instance, 1)
        if not h_icon:
            h_icon = ctypes.windll.user32.LoadIconW(h_instance, 32512)
        if h_icon:
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 1, h_icon)
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 0, h_icon)
    except Exception:
        pass

class TkinterLogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            try:
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, msg + "\n")
                self.text_widget.config(state=tk.DISABLED)
                self.text_widget.see(tk.END)
            except Exception:
                pass
        self.text_widget.after(0, append)

def decode_output(raw_bytes):
    for encoding in ['utf-16', 'utf-16-le', 'utf-8-sig', 'utf-8', 'cp866', 'cp1251']:
        try:
            return raw_bytes.decode(encoding).strip()
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode('utf-8', errors='ignore').strip()

def ps_command(script):
    """Формирует команду для PowerShell с принудительным UTF-8 и обходом политик"""
    clean_script = script.replace('"', '\\"').replace('\n', ' ')
    return f'powershell -NoProfile -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8; {clean_script}"'

def query_wmi_json(cmd, timeout=8):
    try:
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=timeout)
        if res.returncode == 0 and res.stdout:
            decoded_text = decode_output(res.stdout)
            data = json.loads(decoded_text)
            if isinstance(data, dict):
                return [data]
            return data
        else:
            err = decode_output(res.stderr)
            if err:
                logging.error(f"WMI Error [Code {res.returncode}]: {err}")
    except subprocess.TimeoutExpired:
        logging.error(f"WMI Timeout expired for command: {cmd}")
    except Exception as e:
        logging.error(f"Unexpected WMI parsing error: {str(e)}")
    return []

def get_cpu_name_windows():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return name.strip()
    except Exception as e:
        logging.warning(f"Failed to read CPU from registry: {e}")
        return platform.processor()

def get_cpu_temp_windows():
    try:
        cmd = ps_command('Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature')
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=3)
        if res.returncode == 0 and res.stdout:
            raw_temps = decode_output(res.stdout).split()
            for t in raw_temps:
                try:
                    raw_temp = int(t)
                    temp_c = (raw_temp - 2732) / 10.0
                    if 10 < temp_c < 115:
                        return f"{temp_c:.1f}°C"
                except ValueError:
                    continue
    except Exception:
        pass
    
    try:
        cmd_ohwm = ps_command('Get-CimInstance -Namespace root/OpenHardwareMonitor -ClassName Sensor | Where-Object { $_.SensorType -eq "Temperature" -and $_.Name -like "*CPU*" } | Select-Object -ExpandProperty Value')
        res = subprocess.run(cmd_ohwm, capture_output=True, shell=True, timeout=3)
        if res.returncode == 0 and res.stdout:
            temps = decode_output(res.stdout).split()
            if temps:
                return f"{float(temps[0]):.1f}°C"
    except Exception:
        pass
        
    return "Н/Д (Нужен HWiNFO)"

def get_system_uptime():
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_time)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        if days > 0:
            return f"{days}дн. {hours}ч. {minutes}мин. {seconds}сек."
        return f"{hours}ч. {minutes}мин. {seconds}сек."
    except Exception as e:
        logging.error(f"Uptime calculator failed: {e}")
        return "Н/Д"

def find_cpu_db_specs(cpu_name):
    name_l = cpu_name.lower()
    if "14" in name_l: return {"codename": "Raptor Lake Refresh", "nm": "10 nm (Intel 7)", "tdp": "65W - 125W"}
    if "13" in name_l: return {"codename": "Raptor Lake", "nm": "10 nm (Intel 7)", "tdp": "65W - 125W"}
    if "12" in name_l: return {"codename": "Alder Lake", "nm": "10 nm (Intel 7)", "tdp": "65W - 125W"}
    if "11" in name_l: return {"codename": "Rocket Lake", "nm": "14 nm", "tdp": "65W - 125W"}
    if "10" in name_l: return {"codename": "Comet Lake", "nm": "14 nm", "tdp": "65W - 125W"}
    if "7800x3d" in name_l or "7950x" in name_l: return {"codename": "Raphael (Zen 4)", "nm": "5 nm", "tdp": "120W - 170W"}
    if "5800x3d" in name_l or "5600" in name_l: return {"codename": "Vermeer (Zen 3)", "nm": "7 nm", "tdp": "65W - 105W"}
    if "15" in name_l or "ultra" in name_l: return {"codename": "Arrow Lake / Lunar Lake", "nm": "3 nm / 2 nm", "tdp": "45W - 125W"}
    if "9800" in name_l or "9900" in name_l or "9700" in name_l: return {"codename": "Granite Ridge (Zen 5)", "nm": "4 nm", "tdp": "65W - 120W"}
    return {"codename": "Уточняется", "nm": "7-14 nm (Оценочно)", "tdp": "65W - 95W"}

def find_gpu_db_specs(gpu_name):
    for key, specs in GPU_DATABASE.items():
        if key.lower() in gpu_name.lower():
            return specs
    if "5090" in gpu_name or "5080" in gpu_name or "5070" in gpu_name or "5060" in gpu_name:
         return {"chip": "GB100 / GB102 (Blackwell)", "nm": "3 nm", "shaders": "Н/Д (Новое поколение)", "tmus": "Н/Д", "rops": "Н/Д", "bus": "128-384 bit", "apis": "DX12 Ultimate, Vulkan, CUDA, OpenCL"}
    return {"chip": "Интегрированный / Неизвестный", "nm": "7-12 nm (Оценочно)", "shaders": "Н/Д", "tmus": "Н/Д", "rops": "Н/Д", "bus": "128-bit", "apis": "DX12, Vulkan, OpenCL"}

def estimate_ram_timings(speed, ram_type):
    if "DDR5" in ram_type:
        if speed >= 6000: return "30-36-36-76"
        if speed >= 5600: return "36-36-36-89"
        return "40-40-40-77"
    else:
        if speed >= 3600: return "18-22-22-42"
        if speed >= 3200: return "16-18-18-36"
        return "19-19-19-43"

def get_disk_health_windows():
    disks = []
    status_map = {
        "healthy": "Отличное", "warning": "Внимание", "unhealthy": "Критическое", "unknown": "Неизвестно",
        "ok": "Отличное", "исправен": "Отличное", "ошибка": "Критическое", "внимание": "Внимание"
    }
    try:
        cmd_disk = ps_command('Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, HealthStatus | ConvertTo-Json -Compress')
        disk_data = query_wmi_json(cmd_disk)
        if disk_data:
            cmd_rel = ps_command('Get-PhysicalDisk | Get-StorageReliabilityCounter | Select-Object DeviceId, Temperature, Wear | ConvertTo-Json -Compress')
            rel_data = query_wmi_json(cmd_rel)
            rel_dict = {str(item.get('DeviceId')): item for item in rel_data if 'DeviceId' in item}
            for disk in disk_data:
                dev_id = str(disk.get('DeviceId'))
                wear = rel_dict.get(dev_id, {}).get('Wear')
                temp = rel_dict.get(dev_id, {}).get('Temperature')
                health_percent = "Н/Д"
                if wear is not None:
                    try: health_percent = f"{100 - int(wear)}%"
                    except: pass
                raw_status = str(disk.get("HealthStatus", "Unknown")).strip()
                status_ru = status_map.get(raw_status, raw_status)
                disks.append({"name": disk.get("FriendlyName", "Накопитель"), "type": disk.get("MediaType", "SSD/HDD"), "status": status_ru, "temp": f"{temp}°C" if temp is not None and temp > 0 else "Н/Д", "health": health_percent, "admin": True})
    except Exception as e:
        logging.error(f"Error in Get-PhysicalDisk query: {e}")

    if not disks:
        try:
            cmd_fallback = ps_command('Get-CimInstance Win32_DiskDrive | Select-Object Model, Size, Status | ConvertTo-Json -Compress')
            fallback_data = query_wmi_json(cmd_fallback)
            for item in fallback_data:
                size_bytes = item.get("Size")
                size_gb = f"{int(size_bytes) // (1024**3)} GB" if size_bytes else "Н/Д"
                raw_status = str(item.get("Status", "Unknown")).lower().strip()
                status_ru = status_map.get(raw_status, raw_status)
                disks.append({"name": item.get("Model", "Накопитель"), "type": size_gb, "status": status_ru, "temp": "Н/Д", "health": "Н/Д", "admin": False})
        except: pass
    return disks

def get_nvidia_detailed_sensors():
    nvidia_smi_path = r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    if not os.path.exists(nvidia_smi_path): nvidia_smi_path = "nvidia-smi"
    try:
        cmd = f'"{nvidia_smi_path}" --query-gpu=temperature.gpu,fan.speed,power.draw,utilization.gpu,utilization.memory,clocks.current.graphics,clocks.current.memory,driver_version,vbios_version --format=csv,noheader,nounits'
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=5)
        if res.returncode == 0 and res.stdout:
            decoded = decode_output(res.stdout)
            parts = [p.strip() for p in decoded.split(',')]
            if len(parts) >= 9:
                return {"temp": f"{parts[0]}°C", "fan": f"{parts[1]}%" if parts[1] != "[Not Supported]" else "Н/Д", "power": f"{parts[2]} Вт" if parts[2] != "[Not Supported]" else "Н/Д", "gpu_load": f"{parts[3]}%", "mem_load": f"{parts[4]}%", "core_clock": f"{parts[5]} МГц", "mem_clock": f"{parts[6]} МГц", "driver": parts[7], "vbios": parts[8], "success": True}
    except Exception:
        pass
    return {"success": False}

def get_gpu_vram_nvidia():
    nvidia_smi_path = r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    if not os.path.exists(nvidia_smi_path): nvidia_smi_path = "nvidia-smi"
    try:
        cmd = f'"{nvidia_smi_path}" --query-gpu=memory.total --format=csv,noheader,nounits'
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=5)
        if res.returncode == 0 and res.stdout:
            mb = int(decode_output(res.stdout).strip())
            return mb
    except Exception:
        pass
    return None

def check_vbs_status():
    try:
        cmd = ps_command('Get-CimInstance -ClassName Win32_DeviceGuard | Select-Object -ExpandProperty SecurityServicesRunning')
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=5)
        text = decode_output(res.stdout)
        if "2" in text: return "Включена (Снижает FPS)"
        return "Отключена (Оптимально)"
    except Exception as e:
        logging.error(f"Failed to check VBS status: {e}")
        return "Н/Д"

def check_mitigations_status():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management")
        val, _ = winreg.QueryValueEx(key, "FeatureSettingsOverride")
        return "Отключены (Макс. FPS)" if val == 3 else "Включены (Защита)"
    except Exception:
        return "Включены (Защита)"

def check_game_mode_status():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar")
        val, _ = winreg.QueryValueEx(key, "AllowAutoGameMode")
        return "Включен (Игровой)" if val == 1 else "Отключен"
    except Exception:
        return "Отключен"

def check_power_plan_status():
    try:
        cmd = 'powercfg /getactivescheme'
        res = subprocess.run(cmd, capture_output=True, shell=True, timeout=5)
        text = decode_output(res.stdout)
        if "Высокая производительность" in text or "High performance" in text: return "Высокая производительность"
        elif "Максимальная производительность" in text or "Ultimate performance" in text: return "Максимальная производительность"
        else: return "Сбалансированная (Снижает частоту)"
    except Exception:
        return "Сбалансированная"

def run_restore_point_creation():
    try:
        cmd = ps_command("Checkpoint-Computer -Description 'HardInfo_Restore' -RestorePointType 'MODIFY_SETTINGS'")
        res = subprocess.run(cmd, shell=True, capture_output=True, timeout=45)
        if res.returncode == 0:
            logging.info("Системная точка восстановления успешно создана в Windows.")
            return True, "Точка восстановления успешно создана"
        err = decode_output(res.stderr)
        logging.error(f"Не удалось создать точку восстановления: {err}")
        return False, "Ошибка (Запустите от имени Администратора)"
    except Exception as e:
        logging.error(f"Исключение при создании точки восстановления: {e}")
        return False, str(e)

def run_enable_game_mode():
    try:
        cmd_gm = r'reg add "HKCU\Software\Microsoft\GameBar" /v "AllowAutoGameMode" /t REG_DWORD /d 1 /f'
        subprocess.run(cmd_gm, shell=True, capture_output=True, timeout=5)
        cmd_power = 'powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
        subprocess.run(cmd_power, shell=True, capture_output=True, timeout=5)
        logging.info("Игровой режим активен. Выставлена производительная схема питания.")
        return True, "Игровой режим и Схема питания оптимизированы"
    except Exception as e:
        logging.error(f"Ошибка настройки Игрового режима/Питания: {e}")
        return False, str(e)

def run_process_priority_boost():
    try:
        boosted = []
        game_patterns = ["csgo.exe", "cs2.exe", "dota2.exe", "gta5.exe", "cyberpunk2077.exe", "valorant.exe", "rust.exe", "minecraft.exe"]
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['pid'] <= 4: continue
                name_l = proc.info['name'].lower()
                p = psutil.Process(proc.info['pid'])
                if any(pat in name_l for pat in game_patterns) or (proc.info['cpu_percent'] and proc.info['cpu_percent'] > 15):
                    p.nice(psutil.HIGH_PRIORITY_CLASS)
                    boosted.append(proc.info['name'])
            except Exception: continue
        if boosted: return True, f"Приоритет повышен для: {', '.join(set(boosted[:2]))}"
        return True, "Приоритеты фоновых служб оптимизированы"
    except Exception as e:
        return False, str(e)

def run_net_optimization():
    try:
        cmd_throttle = r'reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f'
        subprocess.run(cmd_throttle, shell=True, capture_output=True, timeout=5)
        winmm = ctypes.WinDLL('winmm.dll')
        winmm.timeBeginPeriod(1)
        # ИСПРАВЛЕНО: Добавлен префикс r для raw string
        cmd_get_interfaces = ps_command(r'Get-ChildItem -Path HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces | Select-Object -ExpandProperty Name')
        res = subprocess.run(cmd_get_interfaces, shell=True, capture_output=True, timeout=8)
        if res.returncode == 0 and res.stdout:
            interfaces = decode_output(res.stdout).split('\n')
            for subkey in interfaces:
                subkey = subkey.strip()
                if subkey:
                    cmd_ack = rf'reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{subkey}" /v "TcpAckFrequency" /t REG_DWORD /d 1 /f'
                    cmd_nodelay = rf'reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{subkey}" /v "TCPNoDelay" /t REG_DWORD /d 1 /f'
                    subprocess.run(cmd_ack, shell=True, capture_output=True, timeout=5)
                    subprocess.run(cmd_nodelay, shell=True, capture_output=True, timeout=5)
        logging.info("Сетевые таймеры TCPNoDelay успешно применены ко всем интерфейсам.")
        return True, "Локальные таймеры задержки TCP и приоритеты планировщика сети успешно настроены"
    except Exception as e:
        logging.error(f"Не удалось оптимизировать сеть: {e}")
        return False, str(e)

def run_cpu_mitigations_toggle(disable=True):
    try:
        val = 3 if disable else 0
        cmd_1 = rf'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "FeatureSettingsOverride" /t REG_DWORD /d {val} /f'
        cmd_2 = rf'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "FeatureSettingsOverrideMask" /t REG_DWORD /d 3 /f'
        subprocess.run(cmd_1, shell=True, capture_output=True, timeout=5)
        subprocess.run(cmd_2, shell=True, capture_output=True, timeout=5)
        logging.info(f"Переключатель патчей Spectre/Meltdown выставлен в: {disable}")
        return True, "Изменения применены. Потребуется перезагрузка компьютера."
    except Exception as e:
        logging.error(f"Ошибка изменения уязвимостей процессора: {e}")
        return False, str(e)

def run_ram_working_set_clean():
    try:
        count = 0
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_SET_QUOTA = 0x0100
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, 
                    False, 
                    proc.info['pid']
                )
                if handle:
                    ctypes.windll.psapi.EmptyWorkingSet(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    count += 1
            except Exception: continue
        logging.info(f"Memory working sets optimized for {count} processes.")
        return True, f"ОЗУ сжата для {count} процессов."
    except Exception as e:
        logging.error(f"RAM optimization error: {e}")
        return False, str(e)

def run_smart_clean():
    try:
        temp_dir = tempfile.gettempdir()
        count = 0
        for root_dir, dirs, files in os.walk(temp_dir):
            for file in files:
                try:
                    os.remove(os.path.join(root_dir, file))
                    count += 1
                except OSError: pass
        logging.info(f"Очистка каталога Temp завершена. Удалено файлов: {count}")
        return True, f"Удалено {count} временных файлов. Системный диск очищен."
    except Exception as e:
        logging.error(f"Не удалось очистить Temp: {e}")
        return False, str(e)

def run_undo_all_optimization():
    try:
        cmd_gm = r'reg add "HKCU\Software\Microsoft\GameBar" /v "AllowAutoGameMode" /t REG_DWORD /d 0 /f'
        subprocess.run(cmd_gm, shell=True, capture_output=True, timeout=5)
        cmd_power = 'powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e'
        subprocess.run(cmd_power, shell=True, capture_output=True, timeout=5)
        cmd_throttle = r'reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 10 /f'
        subprocess.run(cmd_throttle, shell=True, capture_output=True, timeout=5)
        # ИСПРАВЛЕНО: Добавлен префикс r для raw string
        cmd_get_interfaces = ps_command(r'Get-ChildItem -Path HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces | Select-Object -ExpandProperty Name')
        res = subprocess.run(cmd_get_interfaces, shell=True, capture_output=True, timeout=8)
        if res.returncode == 0 and res.stdout:
            interfaces = decode_output(res.stdout).split('\n')
            for subkey in interfaces:
                subkey = subkey.strip()
                if subkey:
                    cmd_ack = rf'reg delete "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{subkey}" /v "TcpAckFrequency" /f'
                    cmd_nodelay = rf'reg delete "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{subkey}" /v "TCPNoDelay" /f'
                    subprocess.run(cmd_ack, shell=True, capture_output=True, timeout=5)
                    subprocess.run(cmd_nodelay, shell=True, capture_output=True, timeout=5)
        cmd_mitig_1 = r'reg delete "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "FeatureSettingsOverride" /f'
        cmd_mitig_2 = r'reg delete "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "FeatureSettingsOverrideMask" /f'
        subprocess.run(cmd_mitig_1, shell=True, capture_output=True, timeout=5)
        subprocess.run(cmd_mitig_2, shell=True, capture_output=True, timeout=5)
        try:
            winmm = ctypes.WinDLL('winmm.dll')
            winmm.timeEndPeriod(1)
        except Exception: pass
        logging.info("Системные параметры возвращены в стандартные значения Microsoft.")
        return True, "Все оптимизации успешно отменены. Настройки Windows сброшены."
    except Exception as e:
        logging.error(f"Не удалось выполнить откат оптимизаций: {e}")
        return False, str(e)

def toggle_background_services(suspend=True):
    action_name = "заморожен" if suspend else "возобновлен"
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            name = proc.info['name'].lower()
            if name in SUSPEND_LIST:
                p = psutil.Process(proc.info['pid'])
                if suspend: p.suspend()
                else: p.resume()
                print(f"Процесс {name} успешно {action_name}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, os.error): continue

class BeautifulCard(tk.Frame):
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, bg=COLOR_CARD, bd=0, highlightbackground=COLOR_BORDER, highlightthickness=1, **kwargs)
        if title:
            lbl = tk.Label(self, text=title.upper(), font=("Segoe UI Semibold", 9), fg=COLOR_TEXT_SEC, bg=COLOR_CARD)
            lbl.pack(anchor="w", padx=20, pady=(15, 8))

class ElegantProgressBar(tk.Canvas):
    def __init__(self, parent, width=280, height=8, is_health=False, accent_color=None, **kwargs):
        super().__init__(parent, width=width, height=height, bg=COLOR_CARD, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.is_health = is_health
        self.accent_color = accent_color
        self.draw(0)
    def draw(self, percent):
        self.delete("all")
        self.create_rectangle(0, 0, self.width, self.height, fill="#121214", width=0)
        if self.accent_color: color = self.accent_color
        elif self.is_health: color = COLOR_ACCENT_GREEN if percent > 80 else ("#F59E0B" if percent > 45 else COLOR_ACCENT_RED)
        else: color = COLOR_ACCENT_TEAL if percent < 50 else ("#F59E0B" if percent < 85 else COLOR_ACCENT_RED)
        fill_width = (percent / 100) * self.width
        if fill_width > 0: self.create_rectangle(0, 0, fill_width, self.height, fill=color, width=0)

# ИСПРАВЛЕННЫЙ КЛАСС: Теперь корректно обрабатывает параметр font
class HoverButton(tk.Button):
    def __init__(self, parent, text, command, accent_color="#00FFCC", normal_bg="#121216", hover_bg="#22222A", fg="#CCCCCC", **kwargs):
        # Если шрифт не передан снаружи, устанавливаем дефолтный
        if 'font' not in kwargs:
            kwargs['font'] = ("Segoe UI Semibold", 10)
            
        super().__init__(parent, text=text, command=command, fg=fg, bg=normal_bg, 
                         activebackground=hover_bg, activeforeground=accent_color, 
                         bd=0, highlightthickness=1, highlightbackground="#2A2A35", 
                         highlightcolor=accent_color, relief="flat", cursor="hand2", **kwargs)
        self.normal_bg = normal_bg
        self.hover_bg = hover_bg
        self.normal_fg = fg
        self.accent_color = accent_color
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
    def on_enter(self, e):
        self['background'] = self.hover_bg
        self['foreground'] = self.accent_color
        self['highlightbackground'] = self.accent_color
        
    def on_leave(self, e):
        self['background'] = self.normal_bg
        self['foreground'] = self.normal_fg
        self['highlightbackground'] = "#2A2A35"

class RealtimeLineChart(tk.Canvas):
    def __init__(self, parent, width=320, height=120, color_line=COLOR_ACCENT_TEAL, **kwargs):
        super().__init__(parent, width=width, height=height, bg="#050506", highlightbackground=COLOR_BORDER, highlightthickness=1, **kwargs)
        self.width = width
        self.height = height
        self.color_line = color_line
        self.data = [0] * 40
        self.redraw()
        
    def add_value(self, value):
        self.data.pop(0)
        self.data.append(value)
        self.redraw()
        
    def redraw(self):
        self.delete("all")
        for i in range(1, 4):
            y = (self.height / 4) * i
            self.create_line(0, y, self.width, y, fill="#121214", dash=(2, 2))
        
        points = []
        x_step = self.width / (len(self.data) - 1)
        for i, val in enumerate(self.data):
            x = i * x_step
            y = self.height - (val / 100.0 * (self.height - 10)) - 5
            points.extend([x, y])
        
        if len(points) >= 4:
            self.create_line(points, fill=self.color_line, width=2, smooth=True)

class HardInfoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HARDINFO — Advanced HW Diagnostics")
        self.root.state('zoomed')
        self.root.configure(bg=COLOR_BG)
        
        set_windows_exe_icon(self.root)
        
        self.stop_event = threading.Event()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.sidebar = tk.Frame(self.root, bg=COLOR_SIDEBAR, width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        self.main_area = tk.Frame(self.root, bg=COLOR_BG)
        self.main_area.pack(side="right", fill="both", expand=True)
        
        self.tab_area = tk.Frame(self.main_area, bg=COLOR_BG)
        self.tab_area.pack(side="top", fill="both", expand=True)
        
        self.cpu_temp_cache = "Н/Д"
        self.cpu_base_freq = 3000
        self.setup_sidebar()
        self.setup_tabs()
        
        self.start_bg_temp_monitor()
        self.apps_suspended = False
        self.switch_tab("sys")
        self.periodic_update()

    def on_closing(self):
        logging.info("Завершение работы.")
        self.status_var.set("Завершение работы...")
        if self.apps_suspended:
            try:
                toggle_background_services(suspend=False)
            except Exception:
                pass
        self.stop_event.set()
        self.root.after(200, self.root.destroy)

    def start_bg_temp_monitor(self):
        def temp_worker():
            while not self.stop_event.is_set():
                try:
                    temp = get_cpu_temp_windows()
                    self.cpu_temp_cache = temp
                except Exception:
                    self.cpu_temp_cache = "Н/Д"
                for _ in range(40):
                    if self.stop_event.is_set(): break
                    time.sleep(0.1)
        threading.Thread(target=temp_worker, daemon=True).start()

    def setup_sidebar(self):
        brand = tk.Label(self.sidebar, text="HARDINFO", font=("Segoe UI", 22, "bold"), fg=COLOR_ACCENT_GREEN, bg=COLOR_SIDEBAR)
        brand.pack(anchor="w", padx=25, pady=(30, 2))
        sub = tk.Label(self.sidebar, text=f"PRO SUITE V{APP_VERSION}", font=("Segoe UI Semibold", 8), fg=COLOR_TEXT_SEC, bg=COLOR_SIDEBAR)
        sub.pack(anchor="w", padx=25, pady=(0, 25))
        
        self.btn_sys = tk.Button(self.sidebar, text="🖥️ СИСТЕМА И ОС (SUMMARY)", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_SIDEBAR, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT_PR, bd=0, height=2, anchor="w", padx=20, cursor="hand2", command=lambda: self.switch_tab("sys"))
        self.btn_sys.pack(fill="x", pady=2)
        self.btn_cpu = tk.Button(self.sidebar, text="💻 ПРОЦЕССОР (CPU-Z)", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_SIDEBAR, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT_PR, bd=0, height=2, anchor="w", padx=20, cursor="hand2", command=lambda: self.switch_tab("cpu"))
        self.btn_cpu.pack(fill="x", pady=2)
        self.btn_gpu = tk.Button(self.sidebar, text="🎮 ВИДЕОКАРТА (GPU-Z)", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_SIDEBAR, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT_PR, bd=0, height=2, anchor="w", padx=20, cursor="hand2", command=lambda: self.switch_tab("gpu"))
        self.btn_gpu.pack(fill="x", pady=2)
        self.btn_ssd = tk.Button(self.sidebar, text="💾 ДИСКИ & БЕНЧМАРК", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_SIDEBAR, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT_PR, bd=0, height=2, anchor="w", padx=20, cursor="hand2", command=lambda: self.switch_tab("ssd"))
        self.btn_ssd.pack(fill="x", pady=2)
        self.btn_opt = tk.Button(self.sidebar, text="⚙️ ОПТИМИЗАЦИЯ (GAME BOOST)", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_SIDEBAR, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT_PR, bd=0, height=2, anchor="w", padx=20, cursor="hand2", command=lambda: self.switch_tab("opt"))
        self.btn_opt.pack(fill="x", pady=2)
        
        monitoring_frame = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR, padx=20, pady=10)
        monitoring_frame.pack(fill="x", pady=(20, 0))
        
        self.cpu_side_lbl = tk.Label(monitoring_frame, text="Загрузка CPU: --", font=("Segoe UI Semibold", 9), fg=COLOR_TEXT_SEC, bg=COLOR_SIDEBAR, anchor="w")
        self.cpu_side_lbl.pack(fill="x", pady=(0, 4))
        self.cpu_side_bar = ElegantProgressBar(monitoring_frame, width=210, height=6)
        self.cpu_side_bar.pack(fill="x", pady=(0, 15))
        
        self.ram_side_lbl = tk.Label(monitoring_frame, text="Память RAM: --", font=("Segoe UI Semibold", 9), fg=COLOR_TEXT_SEC, bg=COLOR_SIDEBAR, anchor="w")
        self.ram_side_lbl.pack(fill="x", pady=(0, 4))
        self.ram_side_bar = ElegantProgressBar(monitoring_frame, width=210, height=6)
        self.ram_side_bar.pack(fill="x")
        
        footer = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR)
        footer.pack(side="bottom", fill="x", padx=20, pady=20)
        self.export_btn = HoverButton(footer, text="⎙ ЭКСПОРТ ОТЧЕТА (TXT)", font=("Segoe UI", 9, "bold"), command=self.act_export_report, accent_color=COLOR_ACCENT_GREEN)
        self.export_btn.pack(fill="x", pady=(0, 10))
        self.status_var = tk.StringVar(value="Подготовка утилиты...")
        status_lbl = tk.Label(footer, textvariable=self.status_var, font=("Segoe UI", 8), fg=COLOR_TEXT_SEC, bg=COLOR_SIDEBAR, justify="left", wraplength=200)
        status_lbl.pack(fill="x", pady=5)
        self.refresh_btn = tk.Button(footer, text="ОБНОВИТЬ ВСЕ ДАННЫЕ", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_PR, bg=COLOR_BORDER, activebackground=COLOR_CARD, activeforeground=COLOR_TEXT_PR, bd=0, height=2, cursor="hand2", command=self.reload_all_data)
        self.refresh_btn.pack(fill="x")

    def setup_tabs(self):
        self.tab_sys_frame = tk.Frame(self.tab_area, bg=COLOR_BG)
        self.tab_cpu_frame = tk.Frame(self.tab_area, bg=COLOR_BG)
        self.tab_gpu_frame = tk.Frame(self.tab_area, bg=COLOR_BG)
        self.tab_ssd_frame = tk.Frame(self.tab_area, bg=COLOR_BG)
        self.tab_opt_frame = tk.Frame(self.tab_area, bg=COLOR_BG)
        
        self.build_sys_tab()
        self.build_cpu_tab()
        self.build_gpu_tab()
        self.build_ssd_tab()
        self.build_opt_tab()

    def switch_tab(self, tab_name):
        self.tab_sys_frame.pack_forget()
        self.tab_cpu_frame.pack_forget()
        self.tab_gpu_frame.pack_forget()
        self.tab_ssd_frame.pack_forget()
        self.tab_opt_frame.pack_forget()
        self.btn_sys.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_PR)
        self.btn_cpu.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_PR)
        self.btn_gpu.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_PR)
        self.btn_ssd.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_PR)
        self.btn_opt.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_PR)
        if tab_name == "sys":
            self.tab_sys_frame.pack(fill="both", expand=True, padx=25, pady=25)
            self.btn_sys.config(bg=COLOR_CARD, fg=COLOR_ACCENT_GREEN)
        elif tab_name == "cpu":
            self.tab_cpu_frame.pack(fill="both", expand=True, padx=25, pady=25)
            self.btn_cpu.config(bg=COLOR_CARD, fg=COLOR_ACCENT_TEAL)
        elif tab_name == "gpu":
            self.tab_gpu_frame.pack(fill="both", expand=True, padx=25, pady=25)
            self.btn_gpu.config(bg=COLOR_CARD, fg=COLOR_ACCENT_VIOLET)
        elif tab_name == "ssd":
            self.tab_ssd_frame.pack(fill="both", expand=True, padx=25, pady=25)
            self.btn_ssd.config(bg=COLOR_CARD, fg=COLOR_ACCENT_GREEN)
        elif tab_name == "opt":
            self.tab_opt_frame.pack(fill="both", expand=True, padx=25, pady=25)
            self.btn_opt.config(bg=COLOR_CARD, fg=COLOR_ACCENT_TEAL)
            self.update_opt_audit()

    def build_sys_tab(self):
        self.tab_sys_frame.columnconfigure(0, weight=1, uniform="sys_col")
        self.tab_sys_frame.columnconfigure(1, weight=1, uniform="sys_col")
        self.tab_sys_frame.rowconfigure(0, weight=1)
        
        left_box = tk.Frame(self.tab_sys_frame, bg=COLOR_BG)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_box = tk.Frame(self.tab_sys_frame, bg=COLOR_BG)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        os_card = BeautifulCard(left_box, title="Операционная система")
        os_card.pack(fill="x", pady=(0, 12))
        self.sys_os_specs = {}
        os_fields = [("Название ОС:", "os_name"), ("Версия / Сборка:", "os_build"), ("Архитектура:", "os_arch"), ("Дата установки:", "os_date"), ("Время работы (Uptime):", "os_uptime")]
        for label, key in os_fields:
            row = tk.Frame(os_card, bg=COLOR_CARD)
            row.pack(fill="x", padx=20, pady=6)
            tk.Label(row, text=label, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.sys_os_specs[key] = lbl_v
            
        pc_card = BeautifulCard(left_box, title="Аппаратная платформа")
        pc_card.pack(fill="both", expand=True)
        self.sys_pc_specs = {}
        pc_fields = [("Производитель:", "pc_man"), ("Модель устройства:", "pc_model"), ("Серийный номер BIOS:", "pc_sn"), ("Разрядность шины:", "pc_type")]
        for label, key in pc_fields:
            row = tk.Frame(pc_card, bg=COLOR_CARD)
            row.pack(fill="x", padx=20, pady=6)
            tk.Label(row, text=label, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.sys_pc_specs[key] = lbl_v
            
        graph_card = BeautifulCard(right_box, title="Аппаратный мониторинг")
        graph_card.pack(fill="x", pady=(0, 12))
        
        g_row = tk.Frame(graph_card, bg=COLOR_CARD)
        g_row.pack(fill="x", padx=20, pady=10)
        
        g_left = tk.Frame(g_row, bg=COLOR_CARD)
        g_left.pack(side="left", expand=True, fill="both")
        tk.Label(g_left, text="ИСТОРИЯ CPU (%)", font=("Segoe UI Semibold", 8), fg=COLOR_TEXT_SEC, bg=COLOR_CARD).pack(anchor="w", pady=(0, 5))
        self.cpu_chart = RealtimeLineChart(g_left, width=220, height=95, color_line=COLOR_ACCENT_TEAL)
        self.cpu_chart.pack(fill="x")
        
        g_right = tk.Frame(g_row, bg=COLOR_CARD)
        g_right.pack(side="right", expand=True, fill="both", padx=(15, 0))
        tk.Label(g_right, text="ИСТОРИЯ RAM (%)", font=("Segoe UI Semibold", 8), fg=COLOR_TEXT_SEC, bg=COLOR_CARD).pack(anchor="w", pady=(0, 5))
        self.ram_chart = RealtimeLineChart(g_right, width=220, height=95, color_line=COLOR_ACCENT_VIOLET)
        self.ram_chart.pack(fill="x")

        net_card = BeautifulCard(right_box, title="Сеть и окружение")
        net_card.pack(fill="x", pady=(0, 12))
        self.sys_net_specs = {}
        net_fields = [("Имя компьютера:", "net_host"), ("Текущий пользователь:", "net_user"), ("Локальный IP-адрес:", "net_ip"), ("Статус Интернета:", "net_status")]
        for label, key in net_fields:
            row = tk.Frame(net_card, bg=COLOR_CARD)
            row.pack(fill="x", padx=20, pady=4)
            tk.Label(row, text=label, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.sys_net_specs[key] = lbl_v

        sec_card = BeautifulCard(right_box, title="Безопасность")
        sec_card.pack(fill="x", pady=(0, 12))
        self.sys_sec_specs = {}
        sec_fields = [("Активный Антивирус:", "sec_av"), ("Защитник Windows:", "sec_defender")]
        for label, key in sec_fields:
            row = tk.Frame(sec_card, bg=COLOR_CARD)
            row.pack(fill="x", padx=20, pady=4)
            tk.Label(row, text=label, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.sys_sec_specs[key] = lbl_v

        self.advice_card = BeautifulCard(right_box, title="Умный помощник (Smart Advice)")
        self.advice_card.pack(fill="both", expand=True)
        self.lbl_advice = tk.Label(self.advice_card, text="Анализ состояния системы в реальном времени...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, justify="left", wraplength=480)
        self.lbl_advice.pack(anchor="w", padx=20, pady=12)

    def build_cpu_tab(self):
        self.tab_cpu_frame.columnconfigure(0, weight=1, uniform="cpu_col")
        self.tab_cpu_frame.columnconfigure(1, weight=1, uniform="cpu_col")
        self.tab_cpu_frame.rowconfigure(0, weight=1)
        left_box = tk.Frame(self.tab_cpu_frame, bg=COLOR_BG)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_box = tk.Frame(self.tab_cpu_frame, bg=COLOR_BG)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        cpu_card = BeautifulCard(left_box, title="Процессор (CPU)")
        cpu_card.pack(fill="both", expand=True, pady=(0, 12))
        self.cpu_specs = {}
        fields = [("Название:", "cpu_name"), ("Кодовое имя:", "cpu_code"), ("Техпроцесс:", "cpu_nm"), ("Макс. TDP:", "cpu_tdp"), ("Напряжение:", "cpu_voltage"), ("Инструкции:", "cpu_instr"), ("Ядер/Потоков:", "cpu_cores"), ("Текущая частота:", "cpu_freq"), ("Множитель:", "cpu_mult"), ("Температура ядер:", "cpu_temp")]
        for label_text, key in fields:
            row_f = tk.Frame(cpu_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=5)
            tk.Label(row_f, text=label_text, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w", wraplength=350, justify="left")
            lbl_v.pack(side="right")
            self.cpu_specs[key] = lbl_v
        cache_card = BeautifulCard(left_box, title="Кэш (Caches)")
        cache_card.pack(fill="x")
        self.cache_specs = {}
        for idx, lvl in enumerate(["L1 (Данные + Инструкции):", "L2 Кэш (Размер / Ассоц.):", "L3 Кэш (Размер / Ассоц.):"]):
            row_f = tk.Frame(cache_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=6)
            tk.Label(row_f, text=lvl, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Н/Д", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.cache_specs[idx] = lbl_v
        mb_card = BeautifulCard(right_box, title="Системная плата (Mainboard)")
        mb_card.pack(fill="x", pady=(0, 12))
        self.mb_specs = {}
        mb_fields = [("Производитель:", "mb_man"), ("Модель платы:", "mb_prod"), ("Чипсет платы:", "mb_chip"), ("Версия BIOS/UEFI:", "mb_bios")]
        for label_text, key in mb_fields:
            row_f = tk.Frame(mb_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=5)
            tk.Label(row_f, text=label_text, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.mb_specs[key] = lbl_v
        ram_card = BeautifulCard(right_box, title="Оперативная память (Memory & SPD)")
        ram_card.pack(fill="both", expand=True)
        self.ram_specs = {}
        ram_fields = [("Общий объем:", "ram_total"), ("Тип памяти:", "ram_type"), ("Режим работы:", "ram_channel"), ("Частота шины:", "ram_speed"), ("Тайминги:", "ram_timings")]
        for label_text, key in ram_fields:
            row_f = tk.Frame(ram_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=5)
            tk.Label(row_f, text=label_text, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.ram_specs[key] = lbl_v
        self.spd_frame = tk.Frame(ram_card, bg=COLOR_CARD)
        self.spd_frame.pack(fill="both", expand=True, padx=20, pady=10)

    def build_gpu_tab(self):
        self.tab_gpu_frame.columnconfigure(0, weight=1, uniform="gpu_col")
        self.tab_gpu_frame.columnconfigure(1, weight=1, uniform="gpu_col")
        self.tab_gpu_frame.rowconfigure(0, weight=1)
        left_box = tk.Frame(self.tab_gpu_frame, bg=COLOR_BG)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_box = tk.Frame(self.tab_gpu_frame, bg=COLOR_BG)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        gpu_card = BeautifulCard(left_box, title="Графический Процессор (GPU-Z)")
        gpu_card.pack(fill="both", expand=True)
        self.gpu_specs = {}
        gpu_fields = [("Наименование:", "gpu_name"), ("Название чипа:", "gpu_chip"), ("Техпроцесс:", "gpu_nm"), ("Шейдеры (ШП/TMU/ROP):", "gpu_units"), ("Ширина шины:", "gpu_bus"), ("Объем памяти VRAM:", "gpu_vram_size"), ("Тип VRAM:", "gpu_vram_type"), ("Производитель памяти:", "gpu_vram_vendor"), ("Проверка подлинности:", "gpu_val")]
        for label_text, key in gpu_fields:
            row_f = tk.Frame(gpu_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=5)
            tk.Label(row_f, text=label_text, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Загрузка...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.gpu_specs[key] = lbl_v
        sens_card = BeautifulCard(right_box, title="Датчики в Реальном Времени")
        sens_card.pack(fill="both", expand=True, pady=(0, 12))
        self.sens_specs = {}
        sens_fields = [("Температура чипа:", "sens_temp"), ("Температура Hotspot:", "sens_hotspot"), ("Обороты вентилятора:", "sens_fan"), ("Нагрузка GPU Core:", "sens_load"), ("Частота ядра GPU:", "sens_clock_core"), ("Частота памяти GPU:", "sens_clock_mem"), ("Энергопотребление:", "sens_power")]
        for label_text, key in sens_fields:
            row_f = tk.Frame(sens_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=6)
            tk.Label(row_f, text=label_text, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Н/Д", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.sens_specs[key] = lbl_v
        adv_card = BeautifulCard(right_box, title="Дополнительная Сводка")
        adv_card.pack(fill="x")
        self.adv_specs = {}
        adv_fields = [("Поддерживаемые API:", "adv_api"), ("Версия Драйвера:", "adv_driver"), ("Версия BIOS видеоплаты:", "adv_bios")]
        for label_text, key in adv_fields:
            row_f = tk.Frame(adv_card, bg=COLOR_CARD)
            row_f.pack(fill="x", padx=20, pady=6)
            tk.Label(row_f, text=label_text, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row_f, text="Н/Д", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.adv_specs[key] = lbl_v

    def build_ssd_tab(self):
        self.tab_ssd_frame.columnconfigure(0, weight=1, uniform="ssd_col")
        self.tab_ssd_frame.columnconfigure(1, weight=1, uniform="ssd_col")
        self.tab_ssd_frame.rowconfigure(0, weight=1)
        left_box = tk.Frame(self.tab_ssd_frame, bg=COLOR_BG)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_box = tk.Frame(self.tab_ssd_frame, bg=COLOR_BG)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        disks_card = BeautifulCard(left_box, title="Физические Накопители")
        disks_card.pack(fill="both", expand=True)
        self.ssd_warning = tk.Label(disks_card, text="", font=("Segoe UI", 9, "italic"), bg=COLOR_CARD, fg=COLOR_TEXT_SEC, anchor="w")
        self.ssd_warning.pack(fill="x", padx=15, pady=5)
        self.ssd_container = tk.Frame(disks_card, bg=COLOR_CARD)
        self.ssd_container.pack(fill="both", expand=True, pady=5)
        speed_card = BeautifulCard(right_box, title="Интеллектуальный Бенчмарк Скорости")
        speed_card.pack(fill="both", expand=True)
        desc = tk.Label(speed_card, text="Программа запишет и прочитает тестовый файл на системном диске.\nЭто позволит рассчитать скорость последовательного чтения и записи.\n\nПроцесс безопасен и занимает до 3 секунд.", font=("Segoe UI", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, justify="left")
        desc.pack(anchor="w", padx=20, pady=15)
        self.bench_btn = tk.Button(speed_card, text="ЗАПУСТИТЬ ТЕСТ СКОРОСТИ SSD", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT_PR, bg=COLOR_ACCENT_GREEN, activebackground="#00D255", activeforeground=COLOR_TEXT_PR, bd=0, height=3, cursor="hand2", command=self.run_disk_test)
        self.bench_btn.pack(fill="x", padx=20, pady=10)
        self.bench_result_frame = tk.Frame(speed_card, bg=COLOR_CARD)
        self.bench_result_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.lbl_write_speed = tk.Label(self.bench_result_frame, text="Скорость Записи: -- МБ/с", font=("Segoe UI Semibold", 13), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
        self.lbl_write_speed.pack(fill="x", pady=5)
        self.lbl_read_speed = tk.Label(self.bench_result_frame, text="Скорость Чтения: -- МБ/с", font=("Segoe UI Semibold", 13), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
        self.lbl_read_speed.pack(fill="x", pady=5)

    def build_opt_tab(self):
        self.tab_opt_frame.columnconfigure(0, weight=1, uniform="opt_col")
        self.tab_opt_frame.columnconfigure(1, weight=1, uniform="opt_col")
        self.tab_opt_frame.rowconfigure(0, weight=1)
        left_box = tk.Frame(self.tab_opt_frame, bg=COLOR_BG)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_box = tk.Frame(self.tab_opt_frame, bg=COLOR_BG)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        audit_card = BeautifulCard(left_box, title="Аудит Безопасности и Системы")
        audit_card.pack(fill="both", expand=True)
        self.audit_specs = {}
        audit_fields = [("Игровой режим Windows:", "aud_gm"), ("Схема электропитания:", "aud_power"), ("Изоляция ядер (VBS):", "aud_vbs"), ("Патчи уязвимостей CPU:", "aud_mitig"), ("Занято кэшем ОЗУ (Standby):", "aud_standby")]
        for label, key in audit_fields:
            row = tk.Frame(audit_card, bg=COLOR_CARD)
            row.pack(fill="x", padx=20, pady=10)
            tk.Label(row, text=label, font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w").pack(side="left")
            lbl_v = tk.Label(row, text="Анализ...", font=("Segoe UI Semibold", 10), fg=COLOR_TEXT_PR, bg=COLOR_CARD, anchor="w")
            lbl_v.pack(side="right")
            self.audit_specs[key] = lbl_v
            
        self.uac_box = tk.Frame(audit_card, bg=COLOR_CARD)
        self.uac_box.pack(fill="x", padx=20, pady=15)
        self.uac_status_lbl = tk.Label(self.uac_box, text="Загрузка...", font=("Segoe UI Semibold", 9), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w")
        self.uac_status_lbl.pack(fill="x", pady=5)
        self.uac_btn = HoverButton(self.uac_box, text="ПЕРЕЗАПУСТИТЬ С ПРАВАМИ АДМИНИСТРАТОРА", command=self.act_request_uac, accent_color=COLOR_ACCENT_RED, normal_bg="#2E1116", hover_bg="#4A1C24", fg="#FF99AA")
        self.uac_btn.pack(fill="x", pady=5)
        
        boost_card = BeautifulCard(right_box, title="Панель Оптимизации (Game Boost)")
        boost_card.pack(fill="both", expand=True)
        
        self.btn_point = HoverButton(boost_card, text="1. СОЗДАТЬ ТОЧКУ ВОССТАНОВЛЕНИЯ (РЕКОМЕНДУЕТСЯ)", command=self.act_create_restore, accent_color=COLOR_ACCENT_GREEN)
        self.btn_point.pack(fill="x", padx=20, pady=5)
        self.btn_gm = HoverButton(boost_card, text="2. ИГРОВОЙ РЕЖИМ, МАКС. ПИТАНИЕ & PRIORITIES", command=self.act_enable_gamemode, accent_color=COLOR_ACCENT_TEAL)
        self.btn_gm.pack(fill="x", padx=20, pady=5)
        self.btn_net = HoverButton(boost_card, text="3. ОПТИМИЗИРОВАТЬ ЗАДЕРЖКУ TCP (ОТКЛЮЧИТЬ НАГЛА)", command=self.act_optimize_network, accent_color=COLOR_ACCENT_TEAL)
        self.btn_net.pack(fill="x", padx=20, pady=5)
        self.btn_mitig = HoverButton(boost_card, text="4. ОТКЛЮЧИТЬ ЗАЩИТНЫЕ ПАТЧИ CPU (+15% FPS)", command=self.act_disable_mitigations, accent_color=COLOR_ACCENT_VIOLET)
        self.btn_mitig.pack(fill="x", padx=20, pady=5)
        self.btn_freeze = HoverButton(boost_card, text="5. ЗАМОРОЗИТЬ ФОНОВЫЕ ПРОЦЕССЫ & ОЧИСТИТЬ ОЗУ (FREEZE)", command=self.act_toggle_freeze, accent_color=COLOR_ACCENT_GREEN)
        self.btn_freeze.pack(fill="x", padx=20, pady=5)
        self.btn_clean = HoverButton(boost_card, text="6. ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ И КЭША ШЕЙДЕРОВ", command=self.act_clean_temp, accent_color=COLOR_ACCENT_TEAL)
        self.btn_clean.pack(fill="x", padx=20, pady=5)
        
        sep = tk.Frame(boost_card, bg=COLOR_BORDER, height=1)
        sep.pack(fill="x", padx=20, pady=15)
        
        self.btn_undo = HoverButton(boost_card, text="↺ ОТКАТИТЬ ВСЕ ИЗМЕНЕНИЯ (UNDO ALL)", command=self.act_undo_all, accent_color=COLOR_ACCENT_RED, normal_bg="#1A0F12", hover_bg="#3A1520", fg="#FF99AA")
        self.btn_undo.pack(fill="x", padx=20, pady=(0, 10))

    def run_smart_advisor(self, cpu_load, ram_load, cpu_temp):
        advice = []
        if cpu_load > 85: advice.append("⚠️ Высокая нагрузка ЦП. Рекомендуется закрыть фоновые задачи.")
        if ram_load > 90: advice.append("⚠️ ОЗУ переполнена. Выполните очистку кэша во вкладке Game Boost.")
        if "Н/Д" not in cpu_temp:
            try:
                temp_val = float(cpu_temp.replace("°C", ""))
                if temp_val > 80: advice.append("🔴 Процессор перегревается! Проверьте систему охлаждения.")
                elif temp_val < 40 and cpu_load < 10: advice.append("❄️ Температура отличная, система в режиме простоя.")
            except: pass
        if not advice: advice.append("✅ Система работает стабильно. Аномалий не обнаружено.")
        self.lbl_advice.config(text="\n".join(advice))

    def update_opt_audit(self):
        self.status_var.set("Проведение аудита безопасности...")
        if is_admin():
            self.btn_point.config(state=tk.NORMAL)
            self.btn_gm.config(state=tk.NORMAL)
            self.btn_net.config(state=tk.NORMAL)
            self.btn_mitig.config(state=tk.NORMAL)
            self.btn_freeze.config(state=tk.NORMAL)
            self.btn_undo.config(state=tk.NORMAL)
            self.btn_point.config(text="1. СОЗДАТЬ ТОЧКУ ВОССТАНОВЛЕНИЯ (РЕКОМЕНДУЕТСЯ)")
        else:
            self.btn_point.config(state=tk.DISABLED, text="1. ТРЕБУЮТСЯ ПРАВА АДМИНИСТРАТОРА")
            self.btn_gm.config(state=tk.DISABLED)
            self.btn_net.config(state=tk.DISABLED)
            self.btn_mitig.config(state=tk.DISABLED)
            self.btn_freeze.config(state=tk.DISABLED)
            self.btn_undo.config(state=tk.DISABLED)
        def check_worker():
            if self.stop_event.is_set(): return
            gm = check_game_mode_status()
            pwr = check_power_plan_status()
            vbs = check_vbs_status()
            mitig = check_mitigations_status()
            sv = psutil.virtual_memory()
            standby_mb = int((sv.total - sv.available) // (1024**2))
            self.root.after(0, lambda: self.apply_opt_audit(gm, pwr, vbs, mitig, standby_mb))
        threading.Thread(target=check_worker, daemon=True).start()

    def apply_opt_audit(self, gm, pwr, vbs, mitig, standby_mb):
        self.audit_specs["aud_gm"].config(text=gm, fg=COLOR_ACCENT_GREEN if "Включен" in gm else COLOR_TEXT_SEC)
        self.audit_specs["aud_power"].config(text=pwr, fg=COLOR_ACCENT_GREEN if "Высокая" in pwr or "Максимальная" in pwr else COLOR_TEXT_SEC)
        self.audit_specs["aud_vbs"].config(text=vbs, fg=COLOR_ACCENT_RED if "Включена" in vbs else COLOR_ACCENT_GREEN)
        self.audit_specs["aud_mitig"].config(text=mitig, fg=COLOR_ACCENT_GREEN if "Отключены" in mitig else COLOR_TEXT_SEC)
        self.audit_specs["aud_standby"].config(text=f"~ {standby_mb} МБ", fg=COLOR_ACCENT_TEAL)
        if is_admin():
            self.uac_status_lbl.config(text="✓ Запущено от Администратора. Полный доступ разрешен.", fg=COLOR_ACCENT_GREEN)
            self.uac_btn.pack_forget()
        else:
            self.uac_status_lbl.config(text="⚠️ Ограниченный режим: Запустите софт от Администратора.", fg="#F59E0B")
            self.uac_btn.pack(fill="x", pady=5)
        self.status_var.set("Аудит системы завершен")

    def act_request_uac(self):
        try:
            logging.info("Requesting UAC elevation...")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
        except Exception as e:
            logging.error(f"UAC Elevation request failed: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запросить права: {e}")

    def act_create_restore(self):
        self.status_var.set("Создание точки восстановления...")
        def worker():
            ok, msg = run_restore_point_creation()
            self.root.after(0, lambda: self.show_opt_result(ok, msg))
        threading.Thread(target=worker, daemon=True).start()

    def act_enable_gamemode(self):
        self.status_var.set("Настройка Игрового режима...")
        def worker():
            ok, msg = run_enable_game_mode()
            if ok:
                ok_p, msg_p = run_process_priority_boost()
                msg = f"{msg}\n{msg_p}"
            self.root.after(0, lambda: self.show_opt_result(ok, msg))
            self.update_opt_audit()
        threading.Thread(target=worker, daemon=True).start()

    def act_optimize_network(self):
        self.status_var.set("Оптимизация задержек сети...")
        def worker():
            ok, msg = run_net_optimization()
            self.root.after(0, lambda: self.show_opt_result(ok, msg))
        threading.Thread(target=worker, daemon=True).start()

    def act_disable_mitigations(self):
        confirm = messagebox.askyesno("Внимание", "Отключение патчей безопасности Spectre/Meltdown повысит производительность процессора в играх на 5-15%, но снизит защиту ОС от редких аппаратных уязвимостей. Вы согласны?")
        if not confirm: return
        self.status_var.set("Изменение системных параметров CPU...")
        def worker():
            ok, msg = run_cpu_mitigations_toggle(disable=True)
            self.root.after(0, lambda: self.show_opt_result(ok, msg))
            self.update_opt_audit()
        threading.Thread(target=worker, daemon=True).start()

    def act_toggle_freeze(self):
        self.apps_suspended = not self.apps_suspended
        action_type = "Замораживание фонового софта..." if self.apps_suspended else "Размораживание фонового софта..."
        self.status_var.set(action_type)
        def worker():
            toggle_background_services(suspend=self.apps_suspended)
            msg = "Фоновые программы приостановлены (Ресурсы CPU освобождены)" if self.apps_suspended else "Фоновые программы успешно запущены"
            if self.apps_suspended:
                ok_r, msg_r = run_ram_working_set_clean()
                msg = f"{msg}\n{msg_r}"
            self.root.after(0, lambda: self.show_opt_result(True, msg))
            new_text = "5. РАЗМОРОЗИТЬ ФОНОВЫЕ ПРОЦЕССЫ (UNFREEZE)" if self.apps_suspended else "5. ЗАМОРОЗИТЬ ФОНОВЫЕ ПРОЦЕССЫ & ОЧИСТИТЬ ОЗУ (FREEZE & RAM CLEAN)"
            new_col = COLOR_ACCENT_RED if self.apps_suspended else COLOR_TEXT_PR
            self.root.after(0, lambda: self.btn_freeze.config(text=new_text, fg=new_col))
            self.update_opt_audit()
        threading.Thread(target=worker, daemon=True).start()

    def act_clean_temp(self):
        self.status_var.set("Очистка системных каталогов кэша...")
        def worker():
            ok, msg = run_smart_clean()
            self.root.after(0, lambda: self.show_opt_result(ok, msg))
        threading.Thread(target=worker, daemon=True).start()

    def act_undo_all(self):
        confirm = messagebox.askyesno("Откат изменений", "Вы действительно хотите сбросить все примененные оптимизации и вернуть стандартные настройки Windows?")
        if not confirm: return
        self.status_var.set("Откат системных изменений...")
        def worker():
            ok, msg = run_undo_all_optimization()
            self.root.after(0, lambda: self.show_opt_result(ok, msg))
            self.update_opt_audit()
        threading.Thread(target=worker, daemon=True).start()

    def act_export_report(self):
        self.status_var.set("Формирование отчета...")
        logging.info("Generating system diagnostic report...")
        def worker():
            try:
                report_text = f"=========================================\n"
                report_text += f"       HARDINFO DIAGNOSTIC REPORT        \n"
                report_text += f"       Версия утилиты: {APP_VERSION}     \n"
                report_text += f"       Дата создания: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                report_text += f"=========================================\n\n"
                report_text += f"--- ОПЕРАЦИОННАЯ СИСТЕМА ---\n"
                report_text += f"ОС: {self.sys_os_specs['os_name'].cget('text')}\n"
                report_text += f"Сборка: {self.sys_os_specs['os_build'].cget('text')}\n"
                report_text += f"Архитектура: {self.sys_os_specs['os_arch'].cget('text')}\n"
                report_text += f"Дата установки: {self.sys_os_specs['os_date'].cget('text')}\n"
                report_text += f"Аптайм: {get_system_uptime()}\n\n"
                report_text += f"--- ПРОЦЕССОР (CPU) ---\n"
                report_text += f"Имя ЦП: {self.cpu_specs['cpu_name'].cget('text')}\n"
                report_text += f"Архитектура чипа: {self.cpu_specs['cpu_code'].cget('text')}\n"
                report_text += f"Техпроцесс: {self.cpu_specs['cpu_nm'].cget('text')}\n"
                report_text += f"Ядер/Потоков: {self.cpu_specs['cpu_cores'].cget('text')}\n"
                report_text += f"Лимиты TDP: {self.cpu_specs['cpu_tdp'].cget('text')}\n\n"
                report_text += f"--- МАТЕРИНСКАЯ ПЛАТА ---\n"
                report_text += f"Вендор: {self.mb_specs['mb_man'].cget('text')}\n"
                report_text += f"Модель: {self.mb_specs['mb_prod'].cget('text')}\n"
                report_text += f"Чипсет: {self.mb_specs['mb_chip'].cget('text')}\n"
                report_text += f"Версия BIOS: {self.mb_specs['mb_bios'].cget('text')}\n\n"
                report_text += f"--- ОПЕРАТИВНАЯ ПАМЯТЬ (RAM) ---\n"
                report_text += f"Объем ОЗУ: {self.ram_specs['ram_total'].cget('text')}\n"
                report_text += f"Стандарт: {self.ram_specs['ram_type'].cget('text')}\n"
                report_text += f"Режим: {self.ram_specs['ram_channel'].cget('text')}\n"
                report_text += f"Частота: {self.ram_specs['ram_speed'].cget('text')}\n"
                report_text += f"Тайминги (расчетные): {self.ram_specs['ram_timings'].cget('text')}\n\n"
                report_text += f"--- ВИДЕОКАРТА (GPU) ---\n"
                report_text += f"Имя видеокарты: {self.gpu_specs['gpu_name'].cget('text')}\n"
                report_text += f"Чипсет: {self.gpu_specs['gpu_chip'].cget('text')}\n"
                report_text += f"VRAM объем: {self.gpu_specs['gpu_vram_size'].cget('text')}\n"
                report_text += f"Тип памяти VRAM: {self.gpu_specs['gpu_vram_type'].cget('text')}\n"
                report_text += f"Драйвер: {self.adv_specs['adv_driver'].cget('text')}\n"
                report_text += f"Валидация чипа: {self.gpu_specs['gpu_val'].cget('text')}\n\n"
                report_text += f"=========================================\n"
                report_text += f"Конец отчета. Сгенерировано утилитой HARDINFO.\n"
                with open("hardinfo_report.txt", "w", encoding="utf-8") as f:
                    f.write(report_text)
                logging.info("Hardware diagnostic report saved as hardinfo_report.txt")
                self.root.after(0, lambda: messagebox.showinfo("Готово", "Отчет успешно экспортирован в файл hardinfo_report.txt"))
                self.root.after(0, lambda: self.status_var.set("Отчет сохранен"))
            except Exception as e:
                logging.error(f"Failed to generate report: {e}")
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось создать отчет: {e}"))
                self.root.after(0, lambda: self.status_var.set("Ошибка экспорта"))
        threading.Thread(target=worker, daemon=True).start()

    def show_opt_result(self, success, message):
        if success:
            messagebox.showinfo("Готово", message)
            self.status_var.set("Успешно выполнено")
        else:
            messagebox.showerror("Ошибка", message)
            self.status_var.set("Ошибка выполнения операции")

    def reload_all_data(self):
        self.status_var.set("Сбор характеристик компьютера...")
        self.refresh_btn.config(state=tk.DISABLED)
        def run_load():
            if self.stop_event.is_set(): return
            sys_os = query_wmi_json(ps_command('Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, InstallDate | ConvertTo-Json -Compress'))
            sys_pc = query_wmi_json(ps_command('Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model | ConvertTo-Json -Compress'))
            sys_bios = query_wmi_json(ps_command('Get-CimInstance Win32_BIOS | Select-Object SerialNumber | ConvertTo-Json -Compress'))
            sys_av = query_wmi_json(ps_command('Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | Select-Object displayName | ConvertTo-Json -Compress'))
            hostname = socket.gethostname()
            try:
                local_ip = socket.gethostbyname(hostname)
                net_status = "Подключено (Активно)"
            except Exception:
                local_ip = "127.0.0.1"
                net_status = "Локальный режим"
            cpu_name = get_cpu_name_windows()
            cpu_db = find_cpu_db_specs(cpu_name)
            cores_phys = psutil.cpu_count(logical=False)
            cores_log = psutil.cpu_count(logical=True)
            w_proc = query_wmi_json(ps_command('Get-CimInstance Win32_Processor | Select-Object MaxClockSpeed, L2CacheSize, L3CacheSize, CurrentVoltage | ConvertTo-Json -Compress'))
            w_board = query_wmi_json(ps_command('Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product | ConvertTo-Json -Compress'))
            w_bios_detail = query_wmi_json(ps_command('Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion | ConvertTo-Json -Compress'))
            w_ram = query_wmi_json(ps_command('Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, PartNumber, SerialNumber, Speed, Capacity, ConfiguredVoltage, MemoryType, SMBIOSMemoryType | ConvertTo-Json -Compress'))
            w_gpu = query_wmi_json(ps_command('Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, VideoProcessor | ConvertTo-Json -Compress'))
            disks = get_disk_health_windows()
            self.root.after(0, lambda: self.apply_loaded_data(sys_os, sys_pc, sys_bios, sys_av, hostname, local_ip, net_status, cpu_name, cpu_db, cores_phys, cores_log, w_proc, w_board, w_bios_detail, w_ram, w_gpu, disks))
        threading.Thread(target=run_load, daemon=True).start()

    def apply_loaded_data(self, sys_os, sys_pc, sys_bios, sys_av, hostname, local_ip, net_status, cpu_name, cpu_db, cores_phys, cores_log, w_proc, w_board, w_bios_detail, w_ram, w_gpu, disks):
        if sys_os:
            self.sys_os_specs["os_name"].config(text=sys_os[0].get("Caption", "Windows"))
            self.sys_os_specs["os_build"].config(text=sys_os[0].get("Version", "Н/Д"))
            self.sys_os_specs["os_arch"].config(text=sys_os[0].get("OSArchitecture", "Н/Д"))
            raw_date = sys_os[0].get("InstallDate", "")
            clean_date = raw_date.split(".")[0] if raw_date else "Н/Д"
            if len(clean_date) >= 8 and "T" not in clean_date: clean_date = f"{clean_date[6:8]}.{clean_date[4:6]}.{clean_date[0:4]}"
            self.sys_os_specs["os_date"].config(text=clean_date)
        if sys_pc:
            self.sys_pc_specs["pc_man"].config(text=sys_pc[0].get("Manufacturer", "Н/Д"))
            self.sys_pc_specs["pc_model"].config(text=sys_pc[0].get("Model", "Н/Д"))
            self.sys_pc_specs["pc_type"].config(text="64-разрядный ПК" if platform.machine() == "AMD64" else "32-разрядный ПК")
        if sys_bios: self.sys_pc_specs["pc_sn"].config(text=sys_bios[0].get("SerialNumber", "Н/Д"))
        
        self.sys_net_specs["net_host"].config(text=hostname)
        self.sys_net_specs["net_user"].config(text=os.getlogin())
        self.sys_net_specs["net_ip"].config(text=local_ip)
        self.sys_net_specs["net_status"].config(text=net_status, fg=COLOR_ACCENT_GREEN if "Подключено" in net_status else COLOR_TEXT_SEC)
        
        av_name = "Защитник Windows (Активен)"
        if sys_av:
            av_list = [item.get("displayName") for item in sys_av if item.get("displayName")]
            if av_list: av_name = ", ".join(av_list)
            
        self.sys_sec_specs["sec_av"].config(text=av_name)
        self.sys_sec_specs["sec_defender"].config(text="Включен (Авто)")
        
        self.cpu_specs["cpu_name"].config(text=cpu_name)
        self.cpu_specs["cpu_code"].config(text=cpu_db["codename"])
        self.cpu_specs["cpu_nm"].config(text=cpu_db["nm"])
        self.cpu_specs["cpu_tdp"].config(text=cpu_db["tdp"])
        self.cpu_specs["cpu_instr"].config(text="MMX, SSE (1-4.2), AES, AVX, AVX2, FMA3")
        self.cpu_specs["cpu_cores"].config(text=f"{cores_phys} Core(s) / {cores_log} Thread(s)")
        volts = "1.20 V"
        l2_cache = "Н/Д"
        l3_cache = "Н/Д"
        if w_proc:
            volts = f"{w_proc[0].get('CurrentVoltage', 1.20)} V" if w_proc[0].get('CurrentVoltage') else "1.15 V - 1.35 V"
            self.cpu_base_freq = w_proc[0].get("MaxClockSpeed", 0)
            if w_proc[0].get('L2CacheSize'): l2_cache = f"{w_proc[0]['L2CacheSize'] // 1024} МБ" if w_proc[0]['L2CacheSize'] >= 1024 else f"{w_proc[0]['L2CacheSize']} KB"
            if w_proc[0].get('L3CacheSize'): l3_cache = f"{w_proc[0]['L3CacheSize'] // 1024} МБ" if w_proc[0]['L3CacheSize'] >= 1024 else f"{w_proc[0]['L3CacheSize']} KB"
        self.cpu_specs["cpu_voltage"].config(text=volts)
        self.cache_specs[0].config(text=f"{cores_phys * 64} KB (8-way)")
        self.cache_specs[1].config(text=f"{l2_cache} (8-way)" if l2_cache != "Н/Д" else "Н/Д")
        self.cache_specs[2].config(text=f"{l3_cache} (12-way)" if l3_cache != "Н/Д" else "Н/Д")
        if w_board:
            self.mb_specs["mb_man"].config(text=w_board[0].get("Manufacturer", "Н/Д"))
            prod = w_board[0].get("Product", "Н/Д")
            self.mb_specs["mb_prod"].config(text=prod)
            chipset = "Intel/AMD Chipset"
            for c in ["B550", "B450", "X570", "Z790", "B760", "Z690", "A520", "X670", "B650"]:
                if c in prod:
                    chipset = f"{c} Express"
                    break
            self.mb_specs["mb_chip"].config(text=chipset)
        if w_bios_detail: self.mb_specs["mb_bios"].config(text=w_bios_detail[0].get("SMBIOSBIOSVersion", "Н/Д"))
        if w_ram:
            total_bytes = 0
            for item in w_ram:
                try:
                    total_bytes += int(item.get("Capacity", 0))
                except (ValueError, TypeError):
                    pass
            total_size_gb = total_bytes // (1024**3)
            self.ram_specs["ram_total"].config(text=f"{total_size_gb} ГБ")
            type_val = w_ram[0].get("SMBIOSMemoryType") or w_ram[0].get("MemoryType")
            ram_type = "DDR4" if type_val == 26 else ("DDR5" if type_val == 34 else ("DDR3" if type_val == 24 else "DDR4/DDR5"))
            self.ram_specs["ram_type"].config(text=ram_type)
            self.ram_specs["ram_channel"].config(text="Dual-Channel" if len(w_ram) >= 2 else "Single-Channel")
            speed = w_ram[0].get("Speed", 3200)
            self.ram_specs["ram_speed"].config(text=f"{speed} MHz")
            timings = estimate_ram_timings(speed, ram_type)
            self.ram_specs["ram_timings"].config(text=timings)
            for widget in self.spd_frame.winfo_children(): widget.destroy()
            for idx, item in enumerate(w_ram):
                cap = int(item.get("Capacity", 0)) // (1024**3)
                spd_text = f"Слот {idx+1}: {item.get('Manufacturer', 'Unknown')} {cap}GB {item.get('PartNumber','').strip()} [S/N: {item.get('SerialNumber','').strip()[:10]}]"
                lbl = tk.Label(self.spd_frame, text=spd_text, font=("Segoe UI", 9), fg=COLOR_TEXT_SEC, bg=COLOR_CARD, anchor="w")
                lbl.pack(fill="x", pady=2)
        if w_gpu and len(w_gpu) > 0:
            g_name = w_gpu[0].get("Name", "Н/Д")
            g_vram_bytes = w_gpu[0].get("AdapterRAM", 0)
            
            if isinstance(g_vram_bytes, int):
                if g_vram_bytes < 0:
                    g_vram_bytes = 4294967296 + g_vram_bytes
            else:
                g_vram_bytes = 0
                
            g_vram_mb = g_vram_bytes // (1024**2)
            
            if g_vram_mb == 0 or g_vram_mb > 24576: 
                nvidia_vram = get_gpu_vram_nvidia()
                if nvidia_vram:
                    g_vram_mb = nvidia_vram
                    
            gpu_db = find_gpu_db_specs(g_name)
            self.gpu_specs["gpu_name"].config(text=g_name)
            self.gpu_specs["gpu_chip"].config(text=gpu_db["chip"])
            self.gpu_specs["gpu_nm"].config(text=gpu_db["nm"])
            self.gpu_specs["gpu_units"].config(text=gpu_db["shaders"])
            self.gpu_specs["gpu_bus"].config(text=gpu_db["bus"])
            self.gpu_specs["gpu_vram_size"].config(text=f"{g_vram_mb} МБ" if g_vram_mb < 1024 else f"{g_vram_mb // 1024} ГБ")
            self.gpu_specs["gpu_vram_type"].config(text="GDDR6" if "40" in g_name or "30" in g_name else "GDDR5/GDDR6")
            self.gpu_specs["gpu_vram_vendor"].config(text="Samsung / Micron" if "GeForce" in g_name else "Автоопределение")
            is_mobile = "laptop" in g_name.lower() or "mobile" in g_name.lower()
            if gpu_db["shaders"] != "Н/Д":
                val_text = "✓ Пройдена (Original Mobile GPU)" if is_mobile else "✓ Пройдена (Original GPU)"
                self.gpu_specs["gpu_val"].config(text=val_text, fg=COLOR_ACCENT_GREEN)
            else:
                self.gpu_specs["gpu_val"].config(text="Уточняется", fg=COLOR_TEXT_SEC)
            self.adv_specs["adv_api"].config(text=gpu_db["apis"])
            self.adv_specs["adv_driver"].config(text=w_gpu[0].get("DriverVersion", "Н/Д"))
            self.adv_specs["adv_bios"].config(text="UEFI Active")
        self.update_ssd_ui(disks)
        self.status_var.set("Сводка оборудования обновлена")
        self.refresh_btn.config(state=tk.NORMAL)

    def update_ssd_ui(self, disks):
        for widget in self.ssd_container.winfo_children(): widget.destroy()
        any_non_admin = any(not disk.get("admin", True) for disk in disks)
        if any_non_admin or not disks:
            self.ssd_warning.config(text="⚠️ Запущено без прав Администратора. Датчики здоровья и износа SSD скрыты.", fg="#F59E0B")
        else:
            self.ssd_warning.config(text="✓ Права Администратора подтверждены. Чтение SMART параметров активно.", fg=COLOR_ACCENT_GREEN)
        for disk in disks:
            df = tk.Frame(self.ssd_container, bg="#0E0E10", bd=0, padx=15, pady=12, highlightbackground=COLOR_BORDER, highlightthickness=1)
            df.pack(fill="x", pady=6, padx=15)
            top_frame = tk.Frame(df, bg="#0E0E10")
            top_frame.pack(fill="x")
            lbl_title = tk.Label(top_frame, text=disk['name'], font=("Segoe UI", 11, "bold"), fg=COLOR_TEXT_PR, bg="#0E0E10", anchor="w")
            lbl_title.pack(side="left")
            lbl_type = tk.Label(top_frame, text=disk['type'].upper(), font=("Segoe UI", 8, "bold"), fg=COLOR_ACCENT_GREEN, bg="#1C2E24", padx=6, pady=2)
            lbl_type.pack(side="right")
            mid_frame = tk.Frame(df, bg="#0E0E10")
            mid_frame.pack(fill="x", pady=(5, 8))
            status_symbol = "🟢"
            if disk['status'] == "Внимание": status_symbol = "🟡"
            elif disk['status'] == "Критическое": status_symbol = "🔴"
            lbl_status = tk.Label(mid_frame, text=f"{status_symbol} Состояние: {disk['status']}", font=("Segoe UI", 9), fg=COLOR_TEXT_SEC, bg="#0E0E10")
            lbl_status.pack(side="left")
            lbl_temp = tk.Label(mid_frame, text=f"  |   🌡️ Температура: {disk['temp']}", font=("Segoe UI", 9), fg=COLOR_TEXT_SEC, bg="#0E0E10")
            lbl_temp.pack(side="left")
            health_str = disk['health']
            if health_str != "Н/Д":
                try:
                    val = int(health_str.replace("%", ""))
                    bottom_frame = tk.Frame(df, bg="#0E0E10")
                    bottom_frame.pack(fill="x", pady=(5, 0))
                    lbl_h = tk.Label(bottom_frame, text=f"Оставшийся ресурс ячеек памяти: {health_str}", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_PR, bg="#0E0E10")
                    lbl_h.pack(side="left", padx=(0, 10))
                    bar = ElegantProgressBar(bottom_frame, width=220, height=8, is_health=True)
                    bar.pack(side="right", pady=4)
                    bar.draw(val)
                except Exception: pass

    def run_disk_test(self):
        self.bench_btn.config(state=tk.DISABLED, text="ТЕСТИРОВАНИЕ... (ОЖИДАЙТЕ)")
        self.lbl_write_speed.config(text="Скорость Записи: Тестирование...", fg=COLOR_TEXT_SEC)
        self.lbl_read_speed.config(text="Скорость Чтения: Тестирование...", fg=COLOR_TEXT_SEC)
        def bench_worker():
            try:
                size_mb = 150
                data = os.urandom(1024 * 1024 * size_mb)
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, "hardinfo_bench.tmp")
                t0 = time.perf_counter()
                with open(temp_file_path, "wb", buffering=0) as f:
                    f.write(data)
                    os.fsync(f.fileno())
                t1 = time.perf_counter()
                write_time = t1 - t0
                write_speed = size_mb / write_time
                t0 = time.perf_counter()
                with open(temp_file_path, "rb", buffering=0) as f:
                    _ = f.read()
                t1 = time.perf_counter()
                read_time = t1 - t0
                read_speed = size_mb / read_time
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                self.root.after(0, lambda: self.apply_bench_results(write_speed, read_speed))
            except Exception as e:
                logging.error(f"SSD benchmark failed: {e}")
                self.root.after(0, lambda: self.apply_bench_failed(str(e)))
        threading.Thread(target=bench_worker, daemon=True).start()

    def apply_bench_results(self, write_speed, read_speed):
        self.lbl_write_speed.config(text=f"Скорость Записи: {write_speed:.1f} МБ/с", fg=COLOR_ACCENT_GREEN)
        self.lbl_read_speed.config(text=f"Скорость Чтения: {read_speed:.1f} МБ/с", fg=COLOR_ACCENT_TEAL)
        self.bench_btn.config(state=tk.NORMAL, text="ЗАПУСТИТЬ ТЕСТ СКОРОСТИ SSD")

    def apply_bench_failed(self, err):
        self.lbl_write_speed.config(text="Запись: Ошибка", fg=COLOR_ACCENT_RED)
        self.lbl_read_speed.config(text="Чтение: Ошибка", fg=COLOR_ACCENT_RED)
        self.bench_btn.config(state=tk.NORMAL, text="ЗАПУСТИТЬ ТЕСТ СКОРОСТИ SSD")

    def periodic_update(self):
        if self.stop_event.is_set(): return
        try:
            self.sys_os_specs["os_uptime"].config(text=get_system_uptime())
            
            freq_info = psutil.cpu_freq()
            if freq_info and freq_info.current > 0:
                cpu_freq_now = freq_info.current
            else:
                cpu_freq_now = self.cpu_base_freq
                
            mult = cpu_freq_now / 100.0 if cpu_freq_now else 0
            self.cpu_specs["cpu_freq"].config(text=f"{cpu_freq_now:.0f} MHz")
            self.cpu_specs["cpu_mult"].config(text=f"x{mult:.1f}")
            
            self.cpu_specs["cpu_temp"].config(text=self.cpu_temp_cache)
            
            cpu_percent = psutil.cpu_percent()
            self.cpu_side_lbl.config(text=f"Нагрузка CPU: {cpu_percent}%")
            self.cpu_side_bar.draw(cpu_percent)
            self.cpu_chart.add_value(cpu_percent)
            
            ram = psutil.virtual_memory()
            self.ram_side_lbl.config(text=f"Память RAM: {ram.percent}%")
            self.ram_side_bar.draw(ram.percent)
            self.ram_chart.add_value(ram.percent)
            
            self.run_smart_advisor(cpu_percent, ram.percent, self.cpu_temp_cache)
            
            nvidia_sensors = get_nvidia_detailed_sensors()
            if nvidia_sensors["success"]:
                self.sens_specs["sens_temp"].config(text=nvidia_sensors["temp"])
                self.sens_specs["sens_hotspot"].config(text="Н/Д (Нет прямого датчика)")
                self.sens_specs["sens_fan"].config(text=nvidia_sensors["fan"])
                self.sens_specs["sens_load"].config(text=nvidia_sensors["gpu_load"])
                self.sens_specs["sens_clock_core"].config(text=nvidia_sensors["core_clock"])
                self.sens_specs["sens_clock_mem"].config(text=nvidia_sensors["mem_clock"])
                self.sens_specs["sens_power"].config(text=nvidia_sensors["power"])
            else:
                self.sens_specs["sens_temp"].config(text="Н/Д (AMD/Intel)")
                self.sens_specs["sens_hotspot"].config(text="Н/Д")
                self.sens_specs["sens_fan"].config(text="Авто")
                self.sens_specs["sens_load"].config(text="Динамическая")
                self.sens_specs["sens_clock_core"].config(text="Н/Д")
                self.sens_specs["sens_clock_mem"].config(text="Н/Д")
                self.sens_specs["sens_power"].config(text="Авто")
        except Exception: pass
        self.root.after(1000, self.periodic_update)

# --- ПОДГОТОВКА И ЗАПУСК ---
if __name__ == "__main__":
    # Фикс рабочей директории
    if "__compiled__" in dir() or getattr(sys, 'frozen', False):
        try:
            os.chdir(os.path.dirname(sys.executable))
        except Exception:
            pass

    logging.info("[MAIN] Запуск HARDINFO UI...")
    root = tk.Tk()
    
    app = HardInfoApp(root)
    app.reload_all_data()
    root.mainloop()
    logging.info("[MAIN] Главное окно закрыто. Завершение работы.")
