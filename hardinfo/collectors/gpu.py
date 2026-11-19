"""GPU hardware sensors and utilization querying routines.
"""

import os
import subprocess

try:
    import pynvml  # type: ignore
    pynvml.nvmlInit()
    HAS_PYNVML = True
except Exception:
    pynvml = None
    HAS_PYNVML = False


def get_nvidia_detailed_sensors() -> dict:
    """Queries temperature, fan speed, power draw, and load via nvidia-smi."""
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


def get_amd_intel_gpu_usage_light() -> float:
    """Queries GPU utilization via Windows Performance Counters (WMIC fallback)."""
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
