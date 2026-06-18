Main program features
1. System and OS (Summary)
OS Information: Displays the operating system name, version, build, architecture, installation date, and the exact computer uptime.

Platform Information: Displays the device manufacturer and model (motherboard or laptop), as well as the BIOS serial number.

Network Monitoring: Displays the computer name, current user, local IP address, and internet connection status.

Security: Detects Windows Defender status and the presence of third-party antivirus programs.

Real-time graphs: Visualizes the CPU and RAM load history.

Smart Advice: Automatically analyzes load and temperature indicators, displaying alerts in the event of overheating or critical resource load.

2. Processor (CPU-Z)
CPU Specifications: Identifies the processor model, approximate architecture codename, process technology, thermal design power (TDP), supported instruction set, voltage, and number of cores/threads.

Cache Memory: Displays information about the cache sizes of the first (L1), second (L2), and third (L3) levels.

Motherboard: Displays the motherboard manufacturer, model, chipset, and current BIOS version.

RAM: Provides information about the total memory capacity, its type (DDR3/DDR4/DDR5), operating mode (single-channel/dual-channel), frequency, and estimated timings.

SPD Slots: Reads and organizes information for each installed memory module (manufacturer, serial number, part number).

3. Video Card (GPU-Z)
Technical Specifications: Displays the GPU model, chip codename, manufacturing process, number of shaders/texture units (TMUs)/raster processing units (ROPs), bus width, as well as the amount, type, and manufacturer of video memory.

Real-time Sensors: Displays the current chip temperature, fan speed, core load, processor/memory frequencies, and power consumption in watts (deep monitoring of NVIDIA graphics cards is implemented through the nvidia-smi system utility).

Additionally: Displays supported graphics APIs, the installed driver version, and VBIOS status.

4. Drives & Benchmark
Drive Analysis: Reads physical drive (SSD/HDD) data, displays their S.M.A.R.T. status, current temperature, and the percentage of remaining memory cells (requires administrator privileges).

Express Speed ​​Test: Performs a secure sequential disk test (sequentially writing and then reading a 150 MB test block to a temporary directory) to determine drive speed.

5. Optimization (Game Boost)
System Audit: Checks performance-critical parameters (Windows Game Mode is active, which power plan is in use, whether VBS core isolation is enabled, and the status of processor security patches).

Configuration Tools (the application requires administrator privileges to use):

Create a restore point before making changes.

Enable Windows Game Mode, switch to a high-performance plan, and increase the priority of running game processes.

Reduce network latency by adjusting TCP parameters (disabling the Nagle algorithm).

Disable processor security patches (Spectre/Meltdown) to reduce CPU load in games (with a warning about potential security risks).

Frees up RAM by compressing the working sets of background processes and suspending ("freezing") known non-critical programs (browsers, Discord, etc.).

Cleans up temporary operating system files.

Rolls back all applied changes to Microsoft default settings.
