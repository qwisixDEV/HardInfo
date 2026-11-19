"""Dynamic hardware specifications parser and memory timing estimator.
"""


def parse_hardware_specs_dynamically(hw_name: str, is_gpu: bool = True) -> dict:
    """Infers architecture codename, lithography, TDP, or bus width based on hardware name."""
    name = (hw_name or "").lower()
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


def estimate_ram_timings(speed: int, ram_type: str) -> str:
    """Calculates typical standard RAM timings based on rated speed and generation."""
    if "DDR5" in ram_type:
        if speed >= 6000:
            return "30-36-36-76"
        if speed >= 5600:
            return "36-36-36-89"
        return "40-40-40-77"
    else:
        if speed >= 3600:
            return "18-22-22-42"
        if speed >= 3200:
            return "16-18-18-36"
        return "19-19-19-43"
