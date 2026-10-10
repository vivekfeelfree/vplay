# 🎮 vplay: 2.4GHz Wireless Retro Gamepad RF Sniffer & Emulation Engine

> **A 100% PC-free, Android/Termux-driven RF reverse-engineering platform.**  
> Intercept, decode, and emulate proprietary 2.4GHz wireless retro game stick controllers (`2.4-NEW-XB-1` ASIC) using an **ESP32 DevKit v1** and an **nRF24L01+ PA+LNA (Si24R1)** transceiver directly attached to an Android phone over USB OTG.

---

## ⚡ Overview & Architecture

Modern retro game sticks (Game Stick 4K, Game Stick Lite, etc.) communicate over proprietary, un-encrypted 2.4GHz GFSK wireless airlinks using proprietary ASICs (SOP-16 BK2425/XN297/LT8920 clones). **vplay** turns an Android smartphone into a complete wireless signal analysis lab:

* **Host Engine:** Google Pixel 8 Pro running native Linux userspace via Termux (Python 3.13, PyUSB, esptool).
* **Embedded Transceiver Controller:** ESP32-D0WD-V3 (Dual-Core 240 MHz) running MicroPython v1.22.2 Raw REPL.
* **RF Airlink Radio:** nRF24L01+ / Si24R1 transceiver with Power Amplifier (PA) + Low-Noise Amplifier (LNA) antenna.
* **Interactive UI:** Real-time Web Control Center (`http://localhost:8080`) with auto-scrolling terminal logs, live MicroPython code injection, and 12 hardware diagnostic presets.

---

## 🔌 Hardware Wiring & HSPI Pin Map

The transceiver connects to the ESP32 via the high-speed **HSPI bus** (verified via hardware SPI register dump):

| Transceiver Pin | ESP32 GPIO Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| **VCC** | **3V3** | 3.3V Power Rail | Recommended: Add 10µF capacitor across VCC/GND |
| **GND** | **GND** | Ground Plane | Common ground |
| **SCK** | **GPIO 14** | HSPI Clock | Running at 4.0 MHz SPI clock |
| **MOSI** | **GPIO 13** | HSPI Master-Out | Data out to transceiver |
| **MISO** | **GPIO 12** | HSPI Master-In | Data in from transceiver |
| **CSN** | **GPIO 15** | HSPI Chip Select | Active LOW SPI select |
| **CE** | **GPIO 16 (RX2)** | Chip Enable | RX/TX active strobe |

---

## 🌐 Web Control Center (`http://localhost:8080`)

The background web server provides an interactive HSL glassmorphism dark-mode dashboard:

* **Real-Time Live Hardware Console Stream:** Live execution feedback with auto-scrolling terminal logs.
* **Live MicroPython Code Injector:** Send any custom MicroPython code over USB OTG straight to the chip.
* **Executable Code Inspector:** Inspects the raw Python code executed by every hardware preset.
* **Built-in Presets:**
  1. `🔵 Blink Blue LED (GPIO2)`: Board sanity check and REPL heartbeat.
  2. `🧠 Full SoC & System Diagnostics`: CPU clock, RAM heap, VFS storage, unique MAC.
  3. `🌡️ Internal Thermal & ADC Telemetry`: On-die junction temp (`°F/°C`) and ADC voltages.
  4. `⚡ Universal GPIO Pin Inspector`: 34-pin logic state, voltage, and capability audit.
  5. `💾 Flash Storage & File System`: Reports mounted VFS partition usage.
  6. `⚡ Frequency Scaling`: Clock CPU dynamically to 160 MHz or 240 MHz.
  7. `📡 NRF24 SPI Register Matrix Dump`: Dumps all 24 Si24R1 hardware registers.
  8. `🔍 Auto-Discover NRF24 SPI Pins`: Tests GPIO combinations to auto-detect wiring.
  9. `📶 2.4GHz RF Carrier Sweeper`: Sweeps channels 0–80 (2.400–2.480 GHz) to spot controller bursts.
  10. `🕵️ Universal Promiscuous Preamble Sniffer`: Captures un-addressed packets with CRC disabled.
  11. `🔬 Gamepad Differential Signal Isolator`: 2-phase ambient Wi-Fi noise filter.
  12. `🧹 Memory Garbage Collector`: Reclaims MicroPython heap allocations.

---

## 🔬 Reverse-Engineering Findings & Breakthroughs

1. **Si24R1 Hardware Registers Verified:**
   * `CONFIG = 0x08` (EN_CRC active in reset)
   * `EN_AA = 0x3F` (Auto-ACK enabled)
   * `RF_SETUP = 0x0F` (Si24R1 High-Power +7dBm, 2Mbps GFSK mode)
   * `STATUS = 0x0E` (RX FIFO clear)
2. **Frequency Hopping Spread Spectrum (FHSS):**
   * Controller hops frequencies rapidly across the 2.44GHz – 2.46GHz range.
   * RF carrier energy confirmed primarily on **Channel 38 (2.438 GHz)**, **Channel 48 (2.448 GHz)**, and **Channel 58 (2.458 GHz)**.
3. **Airlink Packet Interception Breakthrough:**
   * Configured 3-byte address width (`SETUP_AW = 0x01`), preamble match `0x55 0x55 0x55`, hardware CRC disabled (`EN_CRC = 0`), and 32-byte payload length.
   * **Successfully captured 138 raw wireless frames over the air** on Channel 58:
     ```text
     FRAME #085 [CH 58] | HEX: [55 55 D5 7D 55 57 55 DD 57 55 6E 6D 95 55 55 57]
     FRAME #089 [CH 58] | HEX: [5D 5D 31 53 55 54 D5 55 65 55 75 29 69 25 4B 54]
     FRAME #105 [CH 58] | HEX: [33 55 4C 4D 34 55 55 51 54 D1 37 95 49 55 14 8B]
     ```
4. **Differential Wi-Fi Noise Filtration:**
   * The 2.4GHz ISM band carries ambient Wi-Fi and Bluetooth traffic. The 2-phase differential test (`scripts/isolate_gamepad.py`) measures baseline idle noise vs. active press bursts to isolate controller packets cleanly.

---

## 🛠️ Repository File Structure

```text
vplay/
├── ESP32_GENERIC-v1.22.2.bin   # Verified MicroPython generic firmware binary
├── JOURNAL.md                  # Comprehensive reverse-engineering laboratory log
├── README.md                   # Project documentation
├── datasheets/                 # CP2102, ESP32, and nRF24L01+ hardware datasheets
│   ├── cp2102_datasheet.pdf
│   ├── esp32_series_datasheet.pdf
│   ├── gamepad_chip_spec.md
│   └── nRF24L01P_datasheet.pdf
└── scripts/                    # Complete Python & MicroPython engineering toolkit
    ├── auto_discover_pins.py   # Automated SPI pin search engine
    ├── blink_blue_led.py       # GPIO2 blink test
    ├── debug_flasher.py        # USB OTG firmware flasher
    ├── esp_flasher.py          # esptool flasher wrapper
    ├── isolate_gamepad.py      # 2-phase differential noise isolator
    ├── live_button_mapper.py   # Real-time bitmask diff tracker
    ├── live_exercise.py        # 9-way framing diagnostic matrix
    ├── nrf24_engine.py         # Register-level driver engine
    ├── probe_all_gpios.py      # 34-pin electrical GPIO & ADC prober
    ├── promiscuous_sniffer.py  # 3-byte preamble sniffer
    ├── repl_cli.py             # Interactive USB REPL terminal
    ├── rf_sniffer_live.py      # Live packet sniffer logger
    ├── server.sh               # Background web server CLI manager
    ├── spi_scanner.py          # SPI bus register dumper
    └── web_server.py           # HTTP Web Control Center
```

---

## 🚀 Quick Start Guide (Termux on Android)

### 1. Prerequisites in Termux
```bash
pkg update && pkg install -y git python libusb termux-api
pip install pyserial pyusb esptool
```

### 2. Connect Hardware
1. Connect ESP32 to Android phone using a USB-C OTG data sync cable.
2. Grant Termux USB access:
   ```bash
   termux-usb -r /dev/bus/usb/001/002
   ```

### 3. Flash MicroPython (if un-flashed)
```bash
python3 scripts/esp_flasher.py
```

### 4. Launch the Web Control Center
```bash
./scripts/server.sh start
```
Open **`http://localhost:8080`** in your browser to interact with the device.

To manage the server at any time:
```bash
./scripts/server.sh status   # Check status
./scripts/server.sh restart  # Restart server
./scripts/server.sh stop     # Stop server
```

---

## 📜 License

MIT License. Created for open-source hardware hacking, radio frequency protocol reverse engineering, and embedded systems education.
