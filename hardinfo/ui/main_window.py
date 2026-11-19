"""Main application window and UI orchestration for HARDINFO.

The window keeps the original GUI behaviour while delegating hardware
collection, data modelling, formatting and system utilities to dedicated
modules.
"""

import ctypes
import logging
import subprocess
import sys

import psutil
import winreg
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hardinfo.collectors import (
    SensorMonitorThread,
    SystemInfoThread,
    estimate_ram_timings,
    parse_hardware_specs_dynamically,
)
from hardinfo.constants import (
    APP_VERSION,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_RED,
    COLOR_ACCENT_TEAL,
    COLOR_ACCENT_VIOLET,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_SIDEBAR,
    COLOR_TEXT_PR,
    COLOR_TEXT_SEC,
)
from hardinfo.formatters import (
    format_cpu_voltage,
    format_memory_capacity,
    format_vram,
)
from hardinfo.models import HardwareProfile
from hardinfo.tweaks_db import TWEAKS_DB
from hardinfo.ui.widgets import (
    AdminWarningBanner,
    ElegantProgressBar,
    HoverCard,
    RealtimeLineChart,
)
from hardinfo.utils import (
    DriverDownloadThread,
    QtLogSignaller,
    QtLoggingHandler,
    SafeRegistryBackup,
    WindowsActivationThread,
    clean_system_string,
)


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
        """Populate hardware tabs from a normalized :class:`HardwareProfile`."""
        profile = HardwareProfile.from_wmi_payload(data)

        # Вкладка 1: ОС
        self.lbl_sys_os.setText(profile.os.name)
        self.lbl_sys_ver.setText(profile.os.version)
        self.lbl_sys_arch.setText(profile.os.architecture)
        self.lbl_sys_pc_man.setText(profile.platform.manufacturer)
        self.lbl_sys_pc_mod.setText(profile.platform.model)
        self.lbl_sys_bios_sn.setText(profile.platform.bios_serial)
        self.lbl_mb_bios.setText(profile.platform.bios_version)

        # Вкладка 2: Процессор
        cpu_name = profile.cpu.name
        self.lbl_cpu_name.setText(clean_system_string(cpu_name))

        cpu_specs = parse_hardware_specs_dynamically(cpu_name, is_gpu=False)
        self.lbl_cpu_code.setText(cpu_specs["codename"])
        self.lbl_cpu_nm.setText(cpu_specs["nm"])
        self.lbl_cpu_tdp.setText(cpu_specs["tdp"])
        self.lbl_cpu_volt.setText(format_cpu_voltage(profile.cpu.voltage))

        self.lbl_board_man.setText(profile.platform.board_manufacturer)
        self.lbl_board_prod.setText(profile.platform.board_product)

        memory = profile.memory
        if memory.module_count:
            self.lbl_ram_cap.setText(format_memory_capacity(memory.total_bytes))
            self.lbl_ram_speed.setText(f"{memory.speed} MHz")
            self.lbl_ram_type.setText(memory.ram_type)
            self.lbl_ram_chan.setText(
                "Dual-Channel" if memory.module_count >= 2 else "Single-Channel"
            )
            self.lbl_ram_timings.setText(
                estimate_ram_timings(memory.speed, memory.ram_type)
            )

        # Вкладка 3: Видеоядро
        gpu_name = profile.gpu.name
        self.lbl_gpu_name.setText(clean_system_string(gpu_name))

        gpu_specs = parse_hardware_specs_dynamically(gpu_name, is_gpu=True)
        self.lbl_gpu_chip.setText(gpu_specs["codename"])
        self.lbl_gpu_nm.setText(gpu_specs["nm"])
        self.lbl_gpu_bus.setText(gpu_specs["bus"])
        self.lbl_gpu_apis.setText(gpu_specs["apis"])
        self.lbl_gpu_driver.setText(profile.gpu.driver_version)
        self.lbl_gpu_proc.setText(profile.gpu.video_processor)
        self.lbl_gpu_cap.setText(format_vram(profile.gpu.adapter_ram_bytes))

        # Нативный вывод версий сетевых и звуковых драйверов
        self.lbl_net_drv_status.setText(profile.network_driver)
        self.lbl_audio_drv_status.setText(profile.audio_driver)
        self.lbl_gpu_drv_status.setText(profile.gpu.driver_version)

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
