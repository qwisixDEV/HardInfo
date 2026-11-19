"""Windows Registry tweaks database categorized by risk/performance profile.
"""

import winreg

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
