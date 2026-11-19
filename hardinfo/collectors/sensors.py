"""Real-time CPU, RAM, and GPU sensor monitoring thread.
"""

import psutil
from PySide6.QtCore import QThread, Signal

from hardinfo.collectors.gpu import (
    HAS_PYNVML,
    get_amd_intel_gpu_usage_light,
)

if HAS_PYNVML:
    import pynvml  # type: ignore


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
                        power_val = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Милливатты в Ватты
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

    def get_fallback_sensors(self, cpu_load: float, ram_load: float) -> dict:
        """Fallback sensor polling for AMD/Intel GPUs via WMIC."""
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
