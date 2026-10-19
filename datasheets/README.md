# 📚 Hardware Datasheets, Drivers & Technical Specifications Catalog

This directory contains the official technical documentation, PDF datasheets, signed Windows CP210x VCP driver, and pinout maps for all hardware components used in **vplay**.

---

## 📂 Catalog of Datasheets & Drivers

### 1. 📘 ESP32 Dual-Core Microcontroller Datasheet
* **Local File:** [esp32_series_datasheet.pdf](./esp32_series_datasheet.pdf)
* **Component:** ESP-WROOM-32 (Espressif Systems Xtensa® Dual-Core LX6)
* **Original Source URL:** [Espressif ESP32 Series Datasheet (PDF)](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf)

### 2. 🔌 CP2102 USB-to-UART Bridge Datasheet & Signed Windows Driver
* **Local Datasheet:** [cp2102_datasheet.pdf](./cp2102_datasheet.pdf)
* **Bundled Windows 10/11 x64 Driver (Microsoft WHQL Signed):** [cp210x_windows_driver/silabser.inf](./cp210x_windows_driver/silabser.inf)
  * Install from an Administrator terminal: `pnputil /add-driver datasheets\cp210x_windows_driver\silabser.inf /install`
* **Component:** Silicon Labs CP2102 Single-Chip USB to UART Bridge (`0x10c4:0xea60`)

### 3. 📡 nRF24L01+ / SI24R1 2.4GHz RF Transceiver Specification
* **Local File:** [nRF24L01P_datasheet.pdf](./nRF24L01P_datasheet.pdf)
* **Component:** Nordic Semiconductor nRF24L01+ / SI24R1 2.4GHz Transceiver + AT2401C PA/LNA

### 4. 🎮 Gamepad Controller Chip Specification (`2.4-NEW-XB-1` PCB)
* **Local File:** [gamepad_chip_spec.md](./gamepad_chip_spec.md)
* **Industry Equivalent SoCs:** **BK2461** (Beken FLIP51 8051 + 2.4G RF) / **XN297L** (Panchip 2.4G Transceiver) / **HS6200**

---

## 🔌 Hardware Wiring Cheat Sheet (ESP32 ➔ nRF24L01+ PA+LNA, Verified HSPI)

```text
  ESP32 (DevKit v1)               nRF24L01+ PA+LNA Board
  ┌───────────────┐               ┌────────────────────┐
  │         3V3   ├──────────────►│ VCC                │ (3.3V Power)
  │         GND   ├──────────────►│ GND                │ (Ground)
  │  GPIO 16 (RX2)├──────────────►│ CE                 │ (Chip Enable)
  │      GPIO 15  ├──────────────►│ CSN                │ (Chip Select)
  │      GPIO 14  ├──────────────►│ SCK                │ (HSPI Clock)
  │      GPIO 13  ├──────────────►│ MOSI               │ (HSPI Master Out)
  │      GPIO 12  ├──────────────►│ MISO               │ (HSPI Master In)
  └───────────────┘               └────────────────────┘
```
