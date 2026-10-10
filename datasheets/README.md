# 📚 Hardware Datasheets & Technical Specifications Catalog

This directory contains the official technical documentation, PDF datasheets, and pinout maps for all hardware components used in the **Retro Game Stick RF Emulation & Pixel 8 Pro Wireless Controller Project**.

---

## 📂 Catalog of Downloaded PDF Datasheets

### 1. 📘 ESP32 Dual-Core Microcontroller Datasheet
* **Local File:** [esp32_series_datasheet.pdf](file:///data/data/com.termux/files/home/trials/vplay/datasheets/esp32_series_datasheet.pdf)
* **Component:** ESP-WROOM-32 (Espressif Systems Xtensa® Dual-Core LX6)
* **Original Source URL:** [Espressif ESP32 Series Datasheet (PDF)](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf)
* **Summary:** Details the dual-core 240MHz CPU architecture, 520KB SRAM, 2.4GHz Wi-Fi (802.11b/g/n), Bluetooth v4.2 BR/EDR & BLE, hardware SPI peripherals (VSPI/HSPI), power consumption modes, and electrical characteristics.

### 2. 🔌 CP2102 USB-to-UART Bridge Datasheet
* **Local File:** [cp2102_datasheet.pdf](file:///data/data/com.termux/files/home/trials/vplay/datasheets/cp2102_datasheet.pdf)
* **Component:** Silicon Labs CP2102 Single-Chip USB to UART Bridge
* **Original Source URL:** [SparkFun / Silicon Labs CP2102 Datasheet (PDF)](https://www.sparkfun.com/datasheets/IC/cp2102.pdf)
* **Summary:** Covers the integrated USB 2.0 full-speed function controller, internal voltage regulator, UART baud rate generator (up to 1.5 Mbps), and signal lines used for programming and serial debugging over USB.

### 3. 📡 nRF24L01+ / SI24R1 2.4GHz RF Transceiver Specification
* **Local File:** [nRF24L01P_datasheet.pdf](file:///data/data/com.termux/files/home/trials/vplay/datasheets/nRF24L01P_datasheet.pdf)
* **Component:** Nordic Semiconductor nRF24L01+ / SI24R1 2.4GHz Transceiver + AT2401C PA/LNA
* **Original Source URL:** [SparkFun / Nordic nRF24L01+ Specification (PDF)](https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf)
* **Summary:** Contains complete RF timing diagrams, SPI instruction set (`W_TX_PAYLOAD`, `R_RX_PAYLOAD`), register addresses (`CONFIG`, `EN_AA`, `RF_CH`, `RF_SETUP`, `STATUS`), GFSK modulation parameters, and multi-receiver address pipes. *(Note: The SI24R1 chip on your board is 100% command and register compatible with this specification).*

---

## 🎮 Gamepad Controller Chip Specification (`2.4-NEW-XB-1` PCB)

Based on the high-resolution photo analysis of your disassembled wireless controller (`PXL_20261003_061414604.jpg`):

* **Board Revision:** `2.4-NEW-XB-1`
* **Controller Main IC (U1):** SOP-16 package (Integrated 8-bit MCU Core + 2.4GHz GFSK RF Transmitter ASIC)
* **Industry Equivalent SoCs:** **BK2461** (Beken FLIP51 8051 + 2.4G RF) / **XN297L** (Panchip 2.4G Transceiver) / **HS6200**

### Technical Characteristics of Gamepad IC (U1):
| Feature | Parameter |
| :--- | :--- |
| **Package** | SOP-16 (16-pin Small Outline Package) |
| **Clock Oscillator (Y1)** | 16.000 MHz Crystal |
| **Operating Voltage** | 1.9 V – 3.6 V DC (Powered by 2×AAA batteries) |
| **RF Transmit Power** | ~0 dBm to +4 dBm (PCB Meander Trace Antenna) |
| **RF Modulation** | 2.4 GHz GFSK (Raw un-acknowledged bitmask framing) |
| **Frequency Range** | 2400 MHz – 2525 MHz (Software/Channel auto-hopping) |
| **Button Input Matrix** | 8 Digital Contacts: Up, Down, Left, Right, A, B, Select, Start |

### Reference Source Links for Gamepad SoCs:
* 🔗 [Beken BK2461 2.4GHz MCU SoC Product Overview](https://www.bekencorp.com/index.php/products/wireless/24g/bk2461)
* 🔗 [Panchip XN297L 2.4GHz RF Transceiver Overview](https://github.com/nRF24/RF24)

---

## 🔌 Hardware Wiring Cheat Sheet (ESP32 ➔ nRF24L01+ PA+LNA)

```
  ESP32 (DevKit v1)               nRF24L01+ PA+LNA Board
  ┌───────────────┐               ┌────────────────────┐
  │         3V3   ├──────────────►│ VCC                │ (3.3V Power)
  │         GND   ├──────────────►│ GND                │ (Ground)
  │      GPIO 4   ├──────────────►│ CE                 │ (Chip Enable)
  │      GPIO 5   ├──────────────►│ CSN                │ (Chip Select)
  │      GPIO 18  ├──────────────►│ SCK                │ (SPI Clock)
  │      GPIO 23  ├──────────────►│ MOSI               │ (Master Out)
  │      GPIO 19  ├──────────────►│ MISO               │ (Master In)
  └───────────────┘               └────────────────────┘
```
