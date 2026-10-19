# 🎮 vplay: Cross-Platform 2.4GHz Wireless Retro Gamepad RF Sniffer & Emulation Engine

> **A unified, platform-agnostic RF reverse-engineering platform for Windows, Linux, macOS, and Android/Termux.**  
> Intercept, decode, and emulate proprietary 2.4GHz wireless retro game stick controllers (`2.4-NEW-XB-1` ASIC) using an **ESP32 DevKit v1** and an **nRF24L01+ PA+LNA (Si24R1)** transceiver connected over USB.

---

## ⚡ Overview & Architecture

Modern retro game sticks (Game Stick 4K, Game Stick Lite, etc.) communicate over proprietary, un-encrypted 2.4GHz GFSK wireless airlinks using SOP-16 ASICs (BK2461 / XN297 / LT8920 equivalents). **vplay** provides a clean, modular Python package (`vplay`) and Web Control Center that runs seamlessly across desktop OSes and Android/Termux:

* **Cross-Platform Host Engine (`vplay`):**
  * **Windows / Linux / macOS:** Uses the `serial` transport (`pyserial`), auto-detecting the Silicon Labs CP2102 bridge (`10c4:ea60`) by USB VID:PID.
  * **Android / Termux:** Uses the `usb` transport (`Cp210xUsbTransport`), speaking the raw CP210x vendor protocol over PyUSB/libusb without requiring root or kernel `/dev/ttyUSB*` drivers.
* **Embedded Transceiver Controller:** ESP32-D0WD-V3 (Dual-Core 240 MHz) running MicroPython v1.22.2 Raw REPL.
* **RF Airlink Radio:** nRF24L01+ / Si24R1 transceiver with Power Amplifier (PA) + Low-Noise Amplifier (LNA) antenna.
* **Interactive Web UI & CLI:** Real-time Web Control Center (`http://127.0.0.1:8080`) and unified `vplay` CLI with 18 built-in hardware & RF presets, live MicroPython code injection, and interactive REPL.

---

## 🔌 Hardware Wiring & HSPI Pin Map

The transceiver connects to the ESP32 via the high-speed **HSPI bus** (configurable in [`vplay.example.toml`](./vplay.example.toml)):

| Transceiver Pin | ESP32 GPIO Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| **VCC** | **3V3** | 3.3V Power Rail | Recommended: Add 10µF capacitor across VCC/GND |
| **GND** | **GND** | Ground Plane | Common ground |
| **SCK** | **GPIO 14** | HSPI Clock | 4.0 MHz SPI clock |
| **MOSI** | **GPIO 13** | HSPI Master-Out | Data out to transceiver |
| **MISO** | **GPIO 12** | HSPI Master-In | Data in from transceiver |
| **CSN** | **GPIO 15** | HSPI Chip Select | Active LOW SPI select |
| **CE** | **GPIO 16 (RX2)** | Chip Enable | RX/TX active strobe |
| **Onboard LED** | **GPIO 2** | Status LED | Blue LED heartbeat |

---

## 🛠️ Repository Structure

```text
vplay/
├── pyproject.toml              # Package metadata & `vplay` console entry point
├── vplay.example.toml          # Optional configuration template (pins, port, web)
├── ESP32_GENERIC-v1.22.2.bin   # Verified MicroPython generic firmware binary
├── JOURNAL.md                  # Reverse-engineering laboratory log
├── README.md                   # Project documentation
├── vplay/                      # Cross-platform Python package
│   ├── hostinfo.py             # OS detection (Windows/Linux/macOS/Android) & UTF-8 console setup
│   ├── config.py               # Single source of truth for pins, device & web config
│   ├── transport/              # Pluggable byte-link backends
│   │   ├── base.py             # Abstract Transport interface
│   │   ├── serial_port.py      # Desktop COM/tty backend (pyserial + Windows PnP diagnostics)
│   │   └── cp210x_usb.py       # Android/Termux raw CP210x USB backend (PyUSB/libusb)
│   ├── repl.py                 # MicroPython Raw-REPL protocol (streaming, raw-paste, timeouts)
│   ├── device.py               # Thread-safe, auto-reconnecting device session
│   ├── flasher.py              # Cross-platform esptool firmware flasher
│   ├── terminal.py             # Cross-platform interactive REPL terminal
│   ├── payloads/               # 18 standalone MicroPython device payloads (.py)
│   ├── web/                    # Local Web Control Center (http://127.0.0.1:8080)
│   └── cli.py                  # Unified `vplay` CLI entry point
├── scripts/                    # Portable CLI/script wrappers + server.sh & server.ps1
├── datasheets/                 # CP2102, ESP32, nRF24L01+ datasheets & signed Windows driver
└── tests/                      # Automated pytest test suite
```

---

## 🚀 Quick Start Guide

### Option A: Windows (PowerShell)

1. **Install the CP2102 Windows VCP Driver (one-time if needed):**  
   If Device Manager shows `CP2102 USB to UART Bridge Controller` with a warning icon (Error Code 28), run once in an **Administrator PowerShell**:
   ```powershell
   pnputil /add-driver ".\datasheets\cp210x_windows_driver\silabser.inf" /install
   ```
   *(Or open `datasheets\cp210x_windows_driver` in File Explorer, right-click `silabser.inf`, and select **Install**).*

2. **Create a virtual environment & install `vplay`:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip install -e ".[dev]"
   ```

3. **Verify hardware connection & run presets:**
   ```powershell
   .\.venv\Scripts\vplay doctor
   .\.venv\Scripts\vplay run blink
   .\.venv\Scripts\vplay run spi_scan
   ```

4. **Launch the Web Control Center (`http://localhost:8080`):**
   ```powershell
   .\.venv\Scripts\vplay web
   # Or manage in the background via PowerShell:
   .\scripts\server.ps1 start
   .\scripts\server.ps1 status
   .\scripts\server.ps1 stop
   ```

---

### Option B: Android (Termux over USB OTG)

1. **Install prerequisites in Termux:**
   ```bash
   pkg update && pkg install -y git python libusb termux-api jq
   pip install -e .
   ```

2. **Connect ESP32 via USB OTG & grant permission:**
   ```bash
   termux-usb -l
   termux-usb -r /dev/bus/usb/001/002
   ```

3. **Launch the Web Control Center or REPL:**
   ```bash
   ./scripts/server.sh start
   ./scripts/server.sh status
   ./scripts/run_repl.sh
   ```

---

## 🧰 Unified `vplay` CLI Commands

| Command | Description |
| :--- | :--- |
| `vplay doctor` | Check host OS, Windows PnP driver state, serial ports, and live ESP32 REPL link |
| `vplay presets` | List all 18 built-in MicroPython hardware & RF analysis presets |
| `vplay run <preset>` | Execute a preset on the ESP32 (`blink`, `specs`, `spi_scan`, `rf_sweep`, `promiscuous`, `isolator`, `button_mapper`, `live_exercise`, ...) |
| `vplay exec "<code>"` | Execute an inline MicroPython snippet or `-f script.py` on the ESP32 |
| `vplay repl` | Open an interactive MicroPython REPL terminal |
| `vplay flash` | Flash `ESP32_GENERIC-v1.22.2.bin` onto the ESP32 |
| `vplay web` | Start the Web Control Center on `http://127.0.0.1:8080` |

---

## 🔬 Reverse-Engineering Findings & Breakthroughs

1. **Si24R1 Hardware Registers Verified:**
   * `CONFIG = 0x08` (`EN_CRC` active in reset), `EN_AA = 0x3F`, `RF_SETUP = 0x0F` (+7dBm, 2Mbps GFSK), `STATUS = 0x0E`.
2. **Frequency Hopping Spread Spectrum (FHSS):**
   * Controller hops across 2.44–2.46 GHz, with primary carrier activity on **Channel 38 (2.438 GHz)**, **Channel 48 (2.448 GHz)**, and **Channel 58 (2.458 GHz)**.
3. **Airlink Packet Interception Breakthrough:**
   * Configured 3-byte address width (`SETUP_AW = 0x01`), preamble match `0x55 0x55 0x55`, hardware CRC disabled (`EN_CRC = 0`), and 32-byte payload length — capturing **138 raw wireless frames over the air** on Channel 58.

---

## 📜 License

MIT License. Created for open-source hardware hacking, radio frequency protocol reverse engineering, and embedded systems education.
