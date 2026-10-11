# 📓 Hardware Engineering Journal & Reverse-Engineering Log

**Project Workspace:** `/data/data/com.termux/files/home/trials/vplay`  
**Host Hardware:** Google Pixel 8 Pro (Termux Android Linux Engine)  
**Target Hardware:** ESP32 DevKit v1 + SI24R1/nRF24L01+ PA+LNA Transceiver + 2.4GHz Game Stick  
**Specs Storage:** `/storage/emulated/0/vwake/tech/specs/`  
**Log Path:** [JOURNAL.md](file:///data/data/com.termux/files/home/trials/vplay/JOURNAL.md)  

---

## 📌 Milestones Roadmap
- [x] **Milestone 0: Hardware Procurement & Datasheets Archiving**
- [x] **Milestone 1: ESP32 Power-On & Factory AP Routing Diagnosis**
- [x] **Milestone 2: USB OTG Data Link & MicroPython Deployment**
- [x] **Milestone 3: 7-Pin SPI Bus Diagnostics & SI24R1 Register Verification**
- [ ] **Milestone 4: 2.4GHz RF Airlink Sniffing & Bitmask Mapping**
- [ ] **Milestone 5: Synthesis, Emulation & Web UI Integration**

---

## 🔬 Experiment Log

### 2026-10-04 | Session 1: ESP32 Factory AP Analysis & Android Routing Findings
* **Actions & Observations:**
  1. Connected ESP32 Dev Board to Pixel 8 Pro via OTG port.
  2. Detected active Wi-Fi AP: `ESP_BA074D`.
  3. **Android Network Routing Conflict:** Connecting phone Wi-Fi to offline `ESP_BA074D` causes Android OS to route all outbound HTTPS traffic through the local ESP32 AP, severing WAN/Internet chat connection.
  4. **Factory AP Service Analysis:** Factory un-flashed ESP32 firmware listens for UDP SmartConfig packets (MAC `BA:07:4D`), not HTTP web pages on port 80.
* **Engineering Decision:**
  * Transitioning to **USB Serial OTG Data Link (Milestone 2)** using a USB Data Sync Cable.
  * This preserves 100% WAN internet connectivity on the Pixel 8 Pro for real-time AI assistant collaboration while granting direct low-level serial access to the ESP32 chip via Termux.

### 2026-10-04 | Session 2: Termux Flashing Toolchain Setup & PySerial Android Patch
* **Actions & Observations:**
  1. **Toolchain Installation:** Successfully installed `esptool v5.4.0`, `pyserial v3.5`, `pyusb v1.3.1`, `bitstring`, `PyYAML`, `intelhex`, `rich`, `click`, and `esp-pylib` in Python 3.13 on Termux.
  2. **PySerial Android Bug Discovery & Fix:**
     - *Issue:* Running `esptool` threw `ImportError: Sorry: no implementation for your platform ('posix') available` because `sys.platform` in Termux Python 3.13 returns `'android'` instead of `'linux'`.
     - *Fix:* Patched `/data/data/com.termux/files/usr/lib/python3.13/site-packages/serial/tools/list_ports_posix.py` line 29 to accept `plat[:7] == 'android'`.
     - *Verification:* Verified `esptool v5.4.0` now loads and executes cleanly natively inside Termux (`esptool v5.4.0`).
  3. **USB OTG Host Interface Inspection:**
     - Queried sysfs (`/sys/bus/usb/devices/`) and Termux USB API (`termux-usb -l`).
     - Found Android OS is currently powering the ESP32 via USB-C port, but OTG Host Data mode requires device node permission / OTG notification confirmation on Pixel 8 Pro.

### 2026-10-04 | Session 3: USB OTG Link Enumeration, Flashing & MicroPython Execution
* **Hardware & Chip Discovery:**
  - **USB Bridge IC:** Silicon Labs CP2102 (`0x10c4:0xea60`, Serial: `0001`).
  - **SoC Model:** ESP32-D0WD-V3 (Revision 3, Dual-Core 240MHz).
  - **Factory MAC:** `68:09:47:ba:07:4c`.
  - **SPI Flash IC:** Winbond `W25Q32JV` (Flash ID `0x16405e` = 4MB SPI Flash).
* **Actions & Results:**
  1. **USB Data Sync Cable Verification:** Swapped to a 4-wire USB data cable; Android immediately enumerated node `/dev/bus/usb/001/002`.
  2. **CP2102 PyUSB Driver Engine:** Created [scripts/debug_flasher.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/debug_flasher.py) bridging PyUSB with `esptool` over Termux file descriptors.
  3. **High-Speed MicroPython Deployment:** Programmed `ESP32_GENERIC-v1.22.2.bin` (1.65 MB) at offset `0x1000` at 460,800 baud in 29.3 seconds. Verified 100% bit-for-bit SHA256 checksum match.
  4. **MicroPython REPL & GPIO Execution:** Executed [scripts/blink_blue_led.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/blink_blue_led.py) using Raw REPL protocol (`\x01`). Onboard Blue LED (`GPIO 2`) successfully blinked 5 times in sync with Python execution.

### 2026-10-04 | Session 4: Web Dashboard Deployment & USB Mutex Resource Management
* **Actions & Observations:**
  1. **Web Dashboard Server:** Created [scripts/web_server.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/web_server.py) providing a modern HSL glassmorphism dark-mode UI accessible at `http://localhost:8080`.
  2. **USB Exclusive Claim (Resource Busy) Analysis:**
     - Attempting to execute terminal CLI (`repl_cli.py`) while `web_server.py` is active in the background resulted in USB `[Errno 16] Resource busy`.
     - *Root Cause:* USB serial controllers (CP2102) permit only a single active PyUSB claim interface session. `web_server.py` retains the connection to serve real-time HTTP requests.
  3. **CLI Terminal Error Handling:**
     - Updated [scripts/repl_cli.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/repl_cli.py) to detect USB lock states gracefully and provide clear instructions to the user.

### 2026-10-04 | Session 5: MicroPython Blue LED Verification & SPI Bus Diagnostics
* **Actions & Observations:**
  1. **Empirical Physical Confirmation:** User verified blue LED (`GPIO 2`) blinking physically on the ESP32 board driven by MicroPython Raw REPL.
  2. **Web Server USB Buffer Flood Fix:**
     - *Issue:* Clicking web buttons on `http://localhost:8080` was not blinking the LED because `run_micropython_script()` toggled RTS/DTR hardware reset lines, causing ROM bootloader output (`try 0x400805cc...`) to flood the RX buffer.
     - *Fix:* Removed hardware RTS/DTR reset toggle and added RX buffer flushing in [scripts/web_server.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/web_server.py).
     - *Verification:* Tested API response: returned `{"success": true, "output": "SUCCESS: Onboard Blue LED (GPIO2) blinked 5 times!"}`.
  3. **Granular Control Engine & Live MicroPython Code Injector:**
     - Created [scripts/nrf24_engine.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/nrf24_engine.py) providing raw register manipulation (`write_reg`, `read_reg`, `write_buf`, `read_buf`, `set_rf_config`, `enable_promiscuous_sniffer`).
     - Upgraded [scripts/web_server.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/web_server.py) with a **Live MicroPython Code Injector UI** and `/api/custom_eval` endpoint, granting 100% dynamic REPL code execution access to the ESP32 over USB OTG.
  4. **SPI Diagnostic Engine Deployment:** Created [scripts/spi_scanner.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/spi_scanner.py) mapping SPI pins: `SCK=GPIO 18`, `MOSI=GPIO 23`, `MISO=GPIO 19`, `CSN=GPIO 5`, `CE=GPIO 4`.
  5. **Initial Register Scan:** Tested SPI bus over USB OTG. SPI read currently returns `0x00` across all registers, indicating module requires physical jumper wiring connection.

### 2026-10-04 | Session 6: Auto-Detection Engine & Fine Granular Presets Suite
* **Actions & Observations:**
  1. **Dynamic USB Auto-Detection Engine:** Implemented `auto_detect_usb_device()` dynamically querying USB host interfaces without relying on fixed node paths (`/dev/bus/usb/001/002`).
  2. **10 Granular Presets Suite:** Added one-click interactive preset suite covering GPIO, CPU clock scaling (160MHz/240MHz), raw thermal sensors (`134°F`), VFS storage stats, SPI dumps, RF carrier sweeping, promiscuous packet sniffing, and RAM garbage collection.
  3. **Continuous Diagnostics Collector:** Added `/api/diagnostics` endpoint returning JSON system health data.
  4. **Executable Code Inspector UI:** Upgraded [scripts/web_server.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/web_server.py) to render the exact Python code for each preset inside an interactive text box on `http://localhost:8080`, automatically populating the Custom Code Injector.
  5. **Sensors Telemetry Formatting Update:** Refactored `sensors` preset to format raw thermal junction output (`134 °F / 56.7 °C`) and added ADC voltage telemetry on GPIO34.
  6. **Automated SPI Pin Discovery Engine:** Created [scripts/auto_discover_pins.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/auto_discover_pins.py) and added `auto_discover` preset on `http://localhost:8080`, dynamically testing candidate GPIO pin combinations (VSPI, HSPI, Alt pinsets) to auto-detect the wired NRF24 transceiver.
  7. **Universal ESP32 GPIO Pin Inspector & Electrical Prober:** Created [scripts/probe_all_gpios.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/probe_all_gpios.py) and added `probe_gpios` preset on `http://localhost:8080`, dynamically auditing all 34 physical GPIO pins (Capabilities: IN/OUT, ADC, Touch, DAC; Live Logic States: HIGH/LOW; Live ADC Voltages: 0.00V-3.30V).

### 2026-10-04 | Session 7: Milestone 3 Complete — HSPI Transceiver Register Verification
* **Actions & Empirical Findings:**
  1. **Physical Wiring & Auto-Discovery Confirmation:** User connected the 7 Dupont jumper wires using HSPI pin mapping (`SCK=GPIO 14`, `MOSI=GPIO 13`, `MISO=GPIO 12`, `CSN=GPIO 15`, `CE=GPIO 4`).
  2. **Automated Register Verification:** Ran `auto_discover` and `spi_scan` over USB OTG. The NRF24 / Si24R1 chip responded with 100% textbook reset values:
     - `CONFIG (0x00)`: `0x08` (EN_CRC active)
     - `EN_AA (0x01)`: `0x3F` (Auto-ACK enabled)
     - `RF_SETUP (0x06)`: `0x0F` (Si24R1 High Power +7dBm, 2Mbps mode)
     - `STATUS (0x07)`: `0x0E` (RX_EMPTY, clear interrupts)
     - `TX_ADDR (0x10)`: `0xE7 0xE7 0xE7 0xE7 0xE7` (5-byte address)
  3. **Milestone Status:** **Milestone 3 100% COMPLETE & VERIFIED.** Transitioning to **Milestone 4: 2.4GHz RF Airlink Sniffing & Bitmask Mapping**.
  4. **Web Server USB Timeout & Script Interrupt Fix:**
     - *Issue:* Running `sniffer_live` previously locked the ESP32 in an 8-second blocking loop while `web_server.py` timed out after 4 seconds, causing serial buffer desynchronization.
     - *Fix:* Added `\x03\x03\x03\x02` (Ctrl+C break) in `run_micropython_script()` and tuned `sniffer_live` duration to 2.5s within a 5.0s HTTP read window.
     - *Verification:* Verified blue LED blink (`GPIO 2`) executes cleanly immediately after running sniffer operations.
  5. **Server Manager CLI Script (`server.sh`):**
     - Created [scripts/server.sh](file:///data/data/com.termux/files/home/trials/vplay/scripts/server.sh) providing simple CLI commands: `./scripts/server.sh start`, `./scripts/server.sh stop`, `./scripts/server.sh restart`, `./scripts/server.sh status`.
### 2026-10-04 | Session 8: Step 2 Promiscuous Sniffing Root Cause Analysis & Airlink Packet Interception Breakthrough
* **User Problem Analysis:**
  - User reported: *"everytime the channel appears to be changing.. sometimes no channel activities detected.. either cases step 2 never intercepts any data.."*
* **Root Cause Diagnostics:**
  1. **Spectrum Sweeper Behavior (Step 1):** Gamepad controllers use Frequency Hopping Spread Spectrum (FHSS) and transmit short (~1ms) burst pulses only when buttons/joysticks are active. Single sweeps catch energy on whichever channel the FHSS sequence lands at that millisecond (e.g. Ch 38, Ch 48, Ch 58), making it appear as if the channel is changing.
  2. **Step 2 Promiscuous Failure Root Cause:** 
     - Previous `promiscuous` preset written to NRF24 contained `w_reg(0x03, 0x00)` (setting Address Width `SETUP_AW = 0x00`). `0x00` is **illegal/reserved** in the NRF24L01/Si24R1 register spec (`0x01` = 3-byte, `0x02` = 4-byte, `0x03` = 5-byte). Setting `SETUP_AW = 0x00` put the receiver hardware into an invalid state, rejecting all incoming preambles.
     - Previous `sniffer_live` preset searched for fixed MAC address `0xE7 0xE7 0xE7 0xE7 0xE7` with CRC enabled. Because the gamepad transmits to its own MAC address, the NRF24 hardware dropped all incoming controller frames.
* **Engineering Fixes & Verification:**
  1. **Fixed Promiscuous Receiver Framing:** Updated [scripts/promiscuous_sniffer.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/promiscuous_sniffer.py) and [scripts/web_server.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/web_server.py):
     - `w_reg(0x03, 0x01)`: 3-byte address width (valid NRF24 spec)
     - `w_buf(0x0A, b'\x55\x55\x55')`: 3-byte preamble wildcard match (`0x55 0x55 0x55`)
     - `w_reg(0x00, 0x03)`: `EN_CRC = 0` (hardware CRC disabled for raw frame capture)
     - `w_reg(0x11, 32)`: 32-byte static payload buffer
  2. **Empirical Airlink Capture Breakthrough:**
     - Ran updated `rf_sweep` preset over USB OTG.
     - **Result:** Intercepted **138 raw 2.4GHz gamepad wireless frames over the air** on **Channel 58 (2.458 GHz)**!
     - *Captured Frame Hex Samples:* `[55 55 D5 7D 55 57 55 DD 57 55 6E 6D 95 55 55 57]`, `[5D 5D 31 53 55 54 D5 55 65 55 75 29 69 25 4B 54]`.
  3. **Live Button Mapper Created:** Created [scripts/live_button_mapper.py](file:///data/data/com.termux/files/home/trials/vplay/scripts/live_button_mapper.py) to isolate exact button bitmasks during user live exercise.

### 2026-10-10 | Session 9: GitHub Repository Creation & Open-Source Publication
* **Actions & Results:**
  1. **Git Initialization & Structure:** Configured [.gitignore](file:///data/data/com.termux/files/home/trials/vplay/.gitignore) and created a comprehensive, production-grade [README.md](file:///data/data/com.termux/files/home/trials/vplay/README.md) detailing architecture, verified pinouts, web dashboard, and sniffing scripts.
  2. **Repository Creation:** Created new public GitHub repository using GitHub CLI (`gh repo create vplay --public`).
  3. **Codebase Pushed:** Committed all 32 files (firmware, laboratory logs, datasheets, Python & MicroPython toolchain) and pushed to branch `main`.
  4. **Live GitHub URL:** [https://github.com/vivekfeelfree/vplay](https://github.com/vivekfeelfree/vplay)












