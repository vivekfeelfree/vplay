# 🎮 Gamepad Controller Chip Specification (`2.4-NEW-XB-1` PCB)

## Overview
This document contains the reverse-engineered hardware architecture and component specifications for the wireless retro gamepad controller identified from the PCB markings in photo `PXL_20261003_061414604.jpg`.

---

## 🛠️ Board Identification & Component Layout

* **Board Revision Marking:** `2.4-NEW-XB-1`
* **Form Factor:** SNES / NES 8-Bit / 16-Bit Style Wireless Gamepad
* **Main Controller IC (U1):** SOP-16 package (Combines 8-bit MCU + 2.4GHz GFSK RF Transmitter ASIC)
* **Oscillator (Y1):** 16.000 MHz Crystal Oscillator
* **Antenna Type:** Onboard PCB Copper Trace Meander Antenna
* **Power Source:** 2 × AAA Batteries (3.0 V DC Nominal)

---

## 📑 Equivalent System-on-Chip (SoC) Architectures

Commercial 2.4 GHz retro game controllers with standard SOP-16 integrated chips utilize one of the following dominant RF SoC architectures:

### 1. Beken BK2461 (FLIP51 MCU + 2.4G RF SoC)
* **CPU Core:** Enhanced 8051-compatible FLIP51 core
* **RF Engine:** 2.4 GHz GFSK Transceiver
* **Data Rates:** 250 kbps, 1 Mbps, 2 Mbps
* **Transmit Power:** Up to +5 dBm
* **Sensitivity:** -93 dBm @ 250 kbps
* **Operating Voltage:** 1.9 V – 3.6 V
* **Datasheet / Product Info Link:** [Beken BK2461 Specification](https://www.bekencorp.com/index.php/products/wireless/24g/bk2461)

### 2. Panchip XN297L Series (2.4G RF Transceiver + MCU)
* **Package:** SOP-16 / QFN-20
* **RF Engine:** 2.4 GHz GFSK (nRF24L01+ protocol subset)
* **Channels:** 125 software-selectable RF channels (2400 MHz – 2525 MHz)
* **Framing:** Un-acknowledged 4-byte to 8-byte payload bitmask
* **Reference Link:** [Panchip XN297L Architecture](https://github.com/nRF24/RF24)

---

## 🕹️ Input Matrix Mapping (PCB Contact Pads)

| Pad Marking | Function | Trigger State |
| :--- | :--- | :--- |
| **U** | D-Pad Up | Pulled to GND when pressed |
| **D** | D-Pad Down | Pulled to GND when pressed |
| **L** | D-Pad Left | Pulled to GND when pressed |
| **R** | D-Pad Right | Pulled to GND when pressed |
| **A** | Action Button A | Pulled to GND when pressed |
| **B** | Action Button B | Pulled to GND when pressed |
| **X** | Action Button X | Pulled to GND when pressed |
| **Y** | Action Button Y | Pulled to GND when pressed |
| **SE** | Select Button | Pulled to GND when pressed |
| **ST** | Start Button | Pulled to GND when pressed |

---

## 📡 Radio Protocol & Emulation Parameters

To emulate or sniff this controller using your **ESP32 + SI24R1/nRF24L01+** setup:

* **Frequency Range:** 2.400 GHz – 2.4835 GHz (Typically centered around Channels 70–84)
* **Modulation:** GFSK
* **Data Rate:** 1 Mbps or 250 kbps
* **Payload Structure:** 4-Byte Bitmask
  * **Byte 0:** Device ID / Preamble Header (e.g., `0xFF` or `0xAA`)
  * **Byte 1:** D-Pad States (`UP`, `DOWN`, `LEFT`, `RIGHT`)
  * **Byte 2:** Action Buttons (`A`, `B`, `X`, `Y`, `SELECT`, `START`)
  * **Byte 3:** Packet Counter / CRC Checksum
