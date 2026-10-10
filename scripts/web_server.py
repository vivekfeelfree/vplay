#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import json
import struct
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import usb.core
import usb.backend.libusb1 as libusb1

REQTYPE_HOST_TO_INTERFACE = 0x41
CP210X_IFC_ENABLE = 0x00
CP210X_SET_BAUD   = 0x1E
CP210X_SET_LINE   = 0x03
CP210X_SET_MHS    = 0x07

usb_lock = threading.Lock()

def auto_detect_usb_device():
    try:
        backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
        dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60, backend=backend)
        if dev is not None:
            return dev
    except Exception:
        pass
    return None

def get_active_usb_device():
    dev = auto_detect_usb_device()
    if dev is None:
        return None
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    try:
        dev.set_configuration()
    except Exception:
        pass
    try:
        dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_IFC_ENABLE, 0x0001, 0, None)
        dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_LINE, 0x0800, 0, None)
        baud_bytes = struct.pack('<I', 115200)
        dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_BAUD, 0, 0, baud_bytes)
    except Exception:
        pass
    return dev

def run_micropython_script(script_text):
    with usb_lock:
        dev = get_active_usb_device()
        if dev is None:
            return {"success": False, "error": "ESP32 USB board not detected. Please connect USB OTG cable."}
        
        try:
            dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, (0x03 << 8) | 0x00, 0, None)
            time.sleep(0.05)
            
            # Send Ctrl+C multiple times + Ctrl+B to interrupt any active script
            dev.write(0x01, b'\x03\x03\x03\x02', timeout=1000)
            time.sleep(0.1)

            # Flush stale buffer
            try:
                while dev.read(0x81, 128, timeout=20):
                    pass
            except Exception:
                pass

            # Enter Raw REPL (Ctrl+A)
            dev.write(0x01, b'\x01', timeout=1000)
            time.sleep(0.1)
            dev.write(0x01, script_text.encode('utf-8') + b'\x04', timeout=1000)
            
            start = time.time()
            output = bytearray()
            while time.time() - start < 5.0:
                try:
                    chunk = dev.read(0x81, 128, timeout=50)
                    if chunk:
                        output.extend(chunk)
                except Exception:
                    pass
                    
            text = output.decode('utf-8', errors='replace')
            return {"success": True, "output": text}
        except Exception as e:
            return {"success": False, "error": f"USB Communication Exception: {str(e)}"}

PRESETS = {
    "blink": {
        "title": "🔵 Blink Blue LED (GPIO2)",
        "desc": "Pulses the onboard blue LED 5 times at 300ms intervals.",
        "script": (
            "import machine, time\n"
            "led = machine.Pin(2, machine.Pin.OUT)\n"
            "for i in range(5):\n"
            "    led.value(1); time.sleep(0.3)\n"
            "    led.value(0); time.sleep(0.3)\n"
            "print('SUCCESS: Onboard Blue LED (GPIO2) blinked 5 times!')\n"
        )
    },
    "specs": {
        "title": "🧠 Full SoC & System Diagnostics",
        "desc": "Retrieves CPU frequency, RAM heap allocations, VFS storage stats, and unique chip ID.",
        "script": (
            "import sys, gc, os, machine, ubinascii\n"
            "print('=== ESP32 FULL SYSTEM SPECS & DIAGNOSTICS ===')\n"
            "print('Platform        :', sys.platform)\n"
            "print('MicroPython Build:', sys.version)\n"
            "print('CPU Frequency   :', machine.freq() // 1000000, 'MHz')\n"
            "print('Chip Unique ID  :', ubinascii.hexlify(machine.unique_id()).decode())\n"
            "print('Reset Reason Code:', machine.reset_cause())\n"
            "print('Free RAM Heap   :', gc.mem_free(), 'bytes')\n"
            "print('Allocated RAM   :', gc.mem_alloc(), 'bytes')\n"
            "print('Storage VFS Stat:', os.statvfs('/'))\n"
        )
    },
    "sensors": {
        "title": "🌡️ Internal Thermal & ADC Telemetry",
        "desc": "Reads the built-in raw temperature sensor (°F and °C) and analog ADC voltage telemetry.",
        "script": (
            "import esp32, machine, time\n"
            "print('=== ESP32 INTERNAL HARDWARE SENSORS & TELEMETRY ===')\n"
            "try:\n"
            "    temp_f = esp32.raw_temperature()\n"
            "    temp_c = (temp_f - 32) * 5.0 / 9.0\n"
            "    print('Internal SoC Junction Temp :', temp_f, '°F (%.1f °C)' % temp_c)\n"
            "except Exception as e: print('Temp Sensor Error:', e)\n"
            "try:\n"
            "    adc = machine.ADC(machine.Pin(34))\n"
            "    print('Analog ADC Input (GPIO34)   :', adc.read(), 'raw (0-4095)')\n"
            "except Exception as e: print('ADC Reading Error:', e)\n"
        )
    },
    "storage": {
        "title": "💾 Flash Storage & File System",
        "desc": "Inspects Flash VFS partition size, used block statistics, and root directory file list.",
        "script": (
            "import os\n"
            "print('=== ESP32 FLASH FILE SYSTEM DIAGNOSTICS ===')\n"
            "stat = os.statvfs('/')\n"
            "total_bytes = stat[0] * stat[2]\n"
            "free_bytes = stat[0] * stat[4]\n"
            "print('Total Flash Storage :', total_bytes // 1024, 'KB')\n"
            "print('Free Flash Storage  :', free_bytes // 1024, 'KB')\n"
            "print('Root Files Listing  :', os.listdir('/'))\n"
        )
    },
    "clock_240": {
        "title": "⚡ Set CPU Frequency to 240 MHz",
        "desc": "Scales ESP32 dual-core clock to maximum performance (240 MHz).",
        "script": (
            "import machine\n"
            "machine.freq(240000000)\n"
            "print('CPU Frequency updated to:', machine.freq() // 1000000, 'MHz [MAX PERFORMANCE]')\n"
        )
    },
    "clock_160": {
        "title": "🌿 Set CPU Frequency to 160 MHz",
        "desc": "Scales ESP32 clock to balanced efficiency mode (160 MHz).",
        "script": (
            "import machine\n"
            "machine.freq(160000000)\n"
            "print('CPU Frequency updated to:', machine.freq() // 1000000, 'MHz [BALANCED]')\n"
        )
    },
    "spi_scan": {
        "title": "📡 NRF24 SPI Register Matrix Dump",
        "desc": "Queries all 14 transceiver registers across VSPI (D18/D23/D19) and HSPI (D14/D13/D12) pin maps.",
        "script": (
            "import machine, time\n"
            "def scan_bus(bus_name, sck_p, mosi_p, miso_p, csn_p, ce_p):\n"
            "    print('=== SCANNING %s PIN CONFIGURATION ===' % bus_name)\n"
            "    print('Pins: SCK=D%d, MOSI=D%d, MISO=D%d, CSN=D%d, CE=D%d' % (sck_p, mosi_p, miso_p, csn_p, ce_p))\n"
            "    sck = machine.Pin(sck_p, machine.Pin.OUT)\n"
            "    mosi = machine.Pin(mosi_p, machine.Pin.OUT)\n"
            "    miso = machine.Pin(miso_p, machine.Pin.IN)\n"
            "    csn = machine.Pin(csn_p, machine.Pin.OUT, value=1)\n"
            "    ce = machine.Pin(ce_p, machine.Pin.OUT, value=0)\n"
            "    spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "    def r_reg(r):\n"
            "        csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]\n"
            "    def r_buf(r, l):\n"
            "        csn.value(0); rx = spi.read(l + 1, r & 0x1F); csn.value(1); return rx[1:]\n"
            "    regs = [('CONFIG', 0x00), ('EN_AA', 0x01), ('EN_RXADDR', 0x02), ('SETUP_AW', 0x03), ('SETUP_RETR', 0x04), ('RF_CH', 0x05), ('RF_SETUP', 0x06), ('STATUS', 0x07)]\n"
            "    for name, addr in regs:\n"
            "        val = r_reg(addr)\n"
            "        print('  %s (0x%02X): 0x%02X (bin: %s)' % (name, addr, val, bin(val)))\n"
            "    tx_addr = r_buf(0x10, 5)\n"
            "    print('  TX_ADDR (0x10): %s\\n' % (' '.join(['0x%02X' % b for b in tx_addr])))\n"
            "scan_bus('VSPI (Default)', 18, 23, 19, 5, 4)\n"
            "scan_bus('HSPI (Alternate)', 14, 13, 12, 15, 4)\n"
        )
    },
    "rf_sweep": {
        "title": "📶 2.4GHz RF Spectrum Carrier Sweeper & Promiscuous Sniffer",
        "desc": "Scans channels 0-80 (2.400-2.480 GHz) while you press buttons, auto-locks onto the active channel, & promiscuously intercepts raw packets without needing target MAC address.",
        "script": (
            "import machine, time\n"
            "def sweep_and_sniff(duration_sec=3.0):\n"
            "    sck = machine.Pin(14, machine.Pin.OUT)\n"
            "    mosi = machine.Pin(13, machine.Pin.OUT)\n"
            "    miso = machine.Pin(12, machine.Pin.IN)\n"
            "    csn = machine.Pin(15, machine.Pin.OUT, value=1)\n"
            "    ce = machine.Pin(16, machine.Pin.OUT, value=0)\n"
            "    try: machine.SPI(1).deinit()\n"
            "    except Exception: pass\n"
            "    spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "    def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)\n"
            "    def w_buf(r, buf): csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)\n"
            "    def r_reg(r): csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]\n"
            "    def r_payload(l=32): csn.value(0); rx = spi.read(l + 1, 0x61); csn.value(1); return rx[1:]\n"
            "    print('======================================================================')\n"
            "    print('📡 STEP 1: SCANNING ALL 80 RF CHANNELS FOR GAMEPAD CARRIER SIGNALS...')\n"
            "    print('   KEEP PRESSING BUTTONS ON YOUR CONTROLLER REPEATEDLY NOW!')\n"
            "    print('======================================================================\\n')\n"
            "    active_chs = {}\n"
            "    ce.value(0)\n"
            "    w_reg(0x00, 0x0F); w_reg(0x01, 0x00); w_reg(0x02, 0x01); w_reg(0x03, 0x03)\n"
            "    w_reg(0x06, 0x0F); w_reg(0x11, 16); w_buf(0x0A, b'\\xE7\\xE7\\xE7\\xE7\\xE7')\n"
            "    ce.value(1)\n"
            "    for ch in range(0, 81, 2):\n"
            "        w_reg(0x05, ch)\n"
            "        time.sleep_ms(8)\n"
            "        rpd = r_reg(0x09) & 0x01\n"
            "        st = r_reg(0x07)\n"
            "        if rpd or (st & 0x40):\n"
            "            active_chs[ch] = active_chs.get(ch, 0) + 1\n"
            "            w_reg(0x07, 0x40)\n"
            "    if active_chs:\n"
            "        print('🎉 Active RF Channels Detected:', active_chs)\n"
            "        best_ch = max(active_chs, key=active_chs.get)\n"
            "        print('   Locking onto Active Controller Channel %d (2.%03d GHz)...\\n' % (best_ch, 400 + best_ch))\n"
            "    else:\n"
            "        print('⚠️ No strong carrier burst on channel sweep. Defaulting to CH 38 (2438 MHz)...\\n')\n"
            "        best_ch = 38\n"
            "    print('======================================================================')\n"
            "    print('🎮 STEP 2: PROMISCUOUS PACKET INTERCEPTOR LOCKED ON CHANNEL %d' % best_ch)\n"
            "    print('   Listening for raw wireless frames (CRC OFF, 3-byte Preamble Match)...')\n"
            "    print('   PRESS AND HOLD GAMEPAD BUTTONS NOW!')\n"
            "    print('======================================================================\\n')\n"
            "    ce.value(0)\n"
            "    w_reg(0x00, 0x03) # PWR_UP=1, PRIM_RX=1, NO_CRC!\n"
            "    w_reg(0x01, 0x00) # Disable Auto-ACK\n"
            "    w_reg(0x02, 0x01) # Enable Pipe 0\n"
            "    w_reg(0x03, 0x01) # 3-byte Address Width\n"
            "    w_reg(0x06, 0x0F) # 2Mbps\n"
            "    w_reg(0x11, 32)   # 32-byte max payload\n"
            "    w_buf(0x0A, b'\\x55\\x55\\x55') # 3-byte 0x55 preamble match\n"
            "    w_reg(0x05, best_ch)\n"
            "    w_reg(0x07, 0x70)\n"
            "    csn.value(0); spi.write(bytes([0xE2])); csn.value(1)\n"
            "    ce.value(1)\n"
            "    start = time.time(); count = 0; last_hex = ''\n"
            "    while time.time() - start < duration_sec:\n"
            "        st = r_reg(0x07); fifo = r_reg(0x17)\n"
            "        if (st & 0x40) or ((fifo & 0x01) == 0):\n"
            "            payload = r_payload(32)\n"
            "            hex_str = ' '.join(['%02X' % b for b in payload[:16]])\n"
            "            if hex_str != last_hex and payload != bytes(32) and payload != b'\\xFF'*32:\n"
            "                count += 1\n"
            "                bin_bits = ' '.join(['{:08b}'.format(b) for b in payload[:4]])\n"
            "                print('FRAME #%03d [CH %2d] | HEX: [%s]' % (count, best_ch, hex_str))\n"
            "                print('                         | BITS: %s' % bin_bits)\n"
            "                last_hex = hex_str\n"
            "            w_reg(0x07, 0x40)\n"
            "        time.sleep_ms(5)\n"
            "    ce.value(0)\n"
            "    print('\\nPromiscuous Sniffing Complete. Total valid frames captured: %d' % count)\n"
            "sweep_and_sniff(3.0)\n"
        )
    },
    "sniffer": {
        "title": "🕵️ 2.4GHz Promiscuous Sniffer Mode",
        "desc": "Configures Pipe 0 for un-addressed promiscuous sniffing on Channel 2.",
        "script": (
            "import machine, time\n"
            "sck = machine.Pin(18, machine.Pin.OUT)\n"
            "mosi = machine.Pin(23, machine.Pin.OUT)\n"
            "miso = machine.Pin(19, machine.Pin.IN)\n"
            "csn = machine.Pin(5, machine.Pin.OUT, value=1)\n"
            "ce = machine.Pin(4, machine.Pin.OUT, value=0)\n"
            "spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)\n"
            "ce.value(0)\n"
            "w_reg(0x00, 0x0F) # PWR_UP, PRIM_RX\n"
            "w_reg(0x01, 0x00) # Disable Auto-ACK\n"
            "w_reg(0x02, 0x01) # Enable Pipe 0\n"
            "w_reg(0x03, 0x03) # 5-byte address width\n"
            "w_reg(0x05, 0x02) # CH 2 (2402 MHz)\n"
            "w_reg(0x06, 0x07) # 1Mbps, +7dBm\n"
            "w_reg(0x11, 16)   # 16-byte payload\n"
            "ce.value(1)\n"
            "print('=== 2.4GHz PROMISCUOUS SNIFFER ACTIVATED ===')\n"
            "print('Listening on 2402 MHz (Channel 2)...')\n"
        )
    },
    "auto_discover": {
        "title": "🔍 Auto-Discover NRF24 SPI Pins",
        "desc": "Dynamically scans GPIO pin combinations (VSPI, HSPI, Alt pinsets) to auto-detect where the NRF24 card is wired.",
        "script": (
            "import machine, time\n"
            "def auto_discover_nrf24():\n"
            "    print('==================================================')\n"
            "    print('🔍 AUTOMATED NRF24 SPI PIN DISCOVERY ENGINE')\n"
            "    print('   Scanning GPIO pins for NRF24/Si24R1 response...')\n"
            "    print('==================================================\\n')\n"
            "    fast_combinations = [\n"
            "        ('HSPI Alt RX2 (CE=RX2/GPIO16)', 14, 13, 12, 15, 16),\n"
            "        ('HSPI Standard (CE=D4)', 14, 13, 12, 15, 4),\n"
            "        ('VSPI Standard (CE=D4)', 18, 23, 19, 5, 4),\n"
            "        ('VSPI Alt RX2 (CE=RX2/GPIO16)', 18, 23, 19, 5, 16),\n"
            "        ('HSPI Alt CSN 5', 14, 13, 12, 5, 4),\n"
            "        ('VSPI Alt CSN 15', 18, 23, 19, 15, 4),\n"
            "        ('Header Group 2', 25, 26, 27, 32, 33),\n"
            "        ('Header Group 3', 27, 14, 12, 13, 15),\n"
            "    ]\n"
            "    found = False\n"
            "    for name, sck_p, mosi_p, miso_p, csn_p, ce_p in fast_combinations:\n"
            "        try:\n"
            "            sck = machine.Pin(sck_p, machine.Pin.OUT)\n"
            "            mosi = machine.Pin(mosi_p, machine.Pin.OUT)\n"
            "            miso = machine.Pin(miso_p, machine.Pin.IN)\n"
            "            csn = machine.Pin(csn_p, machine.Pin.OUT, value=1)\n"
            "            ce = machine.Pin(ce_p, machine.Pin.OUT, value=0)\n"
            "            try: machine.SPI(1).deinit()\n"
            "            except Exception: pass\n"
            "            spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "            csn.value(0); status = spi.read(2, 0x00); csn.value(1)\n"
            "            status_b, config_b = status[0], status[1]\n"
            "            if (status_b != 0x00 and status_b != 0xFF) or (config_b != 0x00 and config_b != 0xFF):\n"
            "                print('🎉 SUCCESS! NRF24 Module Auto-Detected!')\n"
            "                print('   Pin Mapping Identified: [%s]' % name)\n"
            "                print('   SCK  = GPIO %d' % sck_p)\n"
            "                print('   MOSI = GPIO %d' % mosi_p)\n"
            "                print('   MISO = GPIO %d' % miso_p)\n"
            "                print('   CSN  = GPIO %d' % csn_p)\n"
            "                print('   CE   = GPIO %d' % ce_p)\n"
            "                print('   Status Reg (0x07): 0x%02X' % status_b)\n"
            "                print('   Config Reg (0x00): 0x%02X\\n' % config_b)\n"
            "                found = True\n"
            "                break\n"
            "        except Exception as e: pass\n"
            "    if not found:\n"
            "        print('⚠️ No active NRF24 response detected on candidate pins.')\n"
            "        print('   Ensure 3.3V power (VCC) & GND wires are firmly attached.')\n"
            "auto_discover_nrf24()\n"
        )
    },
    "probe_gpios": {
        "title": "⚡ Universal GPIO Pin Inspector & Electrical Prober",
        "desc": "Audits all 34 GPIO pins on the ESP32: discovers capabilities (IN/OUT, ADC, Touch, DAC) and reads live voltages & logic states.",
        "script": (
            "import machine, time\n"
            "def probe_all_gpios():\n"
            "    print('======================================================================')\n"
            "    print('⚡ UNIVERSAL ESP32 GPIO PIN DISCOVERY & ELECTRICAL AUDIT')\n"
            "    print('   Auditing 34 GPIO pins: Capabilities, Live State, ADC Voltages')\n"
            "    print('======================================================================\\n')\n"
            "    all_gpios = [0, 2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35, 36, 39]\n"
            "    input_only = [34, 35, 36, 39]\n"
            "    touch_pins = {4:0, 0:1, 2:2, 15:3, 13:4, 12:5, 14:6, 27:7, 33:8, 32:9}\n"
            "    adc_pins = [32, 33, 34, 35, 36, 39, 4, 0, 2, 13, 12, 14, 27, 25, 26]\n"
            "    for pin_num in all_gpios:\n"
            "        caps = []\n"
            "        if pin_num in input_only: caps.append('INPUT-ONLY')\n"
            "        else: caps.append('IN/OUT')\n"
            "        if pin_num in adc_pins: caps.append('ADC')\n"
            "        if pin_num in touch_pins: caps.append('TOUCH')\n"
            "        if pin_num in [25, 26]: caps.append('DAC')\n"
            "        state_str = ''\n"
            "        try:\n"
            "            p = machine.Pin(pin_num, machine.Pin.IN)\n"
            "            val = p.value()\n"
            "            state_str += 'State: %d (%s)' % (val, 'HIGH/3.3V' if val else 'LOW/0V')\n"
            "        except Exception as e: state_str += 'State: N/A'\n"
            "        if pin_num in [32, 33, 34, 35, 36, 39]:\n"
            "            try:\n"
            "                adc = machine.ADC(machine.Pin(pin_num))\n"
            "                raw_adc = adc.read()\n"
            "                volts = (raw_adc / 4095.0) * 3.3\n"
            "                state_str += ' | Voltage: %.2fV (raw %d)' % (volts, raw_adc)\n"
            "            except Exception: pass\n"
            "        print('GPIO %2d | %-26s | %s' % (pin_num, ', '.join(caps), state_str))\n"
            "    print('\\n======================================================================')\n"
            "probe_all_gpios()\n"
        )
    },
    "sniffer_live": {
        "title": "🎮 Live 2.4GHz Gamepad Packet Sniffer & Logger",
        "desc": "Listens for 2.5 seconds on 2402 MHz (Channel 2), capturing raw 16-byte wireless controller frames & printing hex bitmasks live.",
        "script": (
            "import machine, time\n"
            "def sniff_gamepad_packets(ch=2, duration_sec=2.5):\n"
            "    sck = machine.Pin(14, machine.Pin.OUT)\n"
            "    mosi = machine.Pin(13, machine.Pin.OUT)\n"
            "    miso = machine.Pin(12, machine.Pin.IN)\n"
            "    csn = machine.Pin(15, machine.Pin.OUT, value=1)\n"
            "    ce = machine.Pin(16, machine.Pin.OUT, value=0)\n"
            "    try: machine.SPI(1).deinit()\n"
            "    except Exception: pass\n"
            "    spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "    def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)\n"
            "    def w_buf(r, buf): csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)\n"
            "    def r_reg(r): csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]\n"
            "    def r_payload(length=16): csn.value(0); rx = spi.read(length + 1, 0x61); csn.value(1); return rx[1:]\n"
            "    ce.value(0)\n"
            "    w_reg(0x00, 0x0F)\n"
            "    w_reg(0x01, 0x00)\n"
            "    w_reg(0x02, 0x01)\n"
            "    w_reg(0x03, 0x03)\n"
            "    w_reg(0x05, ch)\n"
            "    w_reg(0x06, 0x0F)\n"
            "    w_reg(0x11, 16)\n"
            "    w_buf(0x0A, b'\\xE7\\xE7\\xE7\\xE7\\xE7')\n"
            "    w_reg(0x07, 0x70)\n"
            "    csn.value(0); spi.write(bytes([0xE2])); csn.value(1)\n"
            "    ce.value(1)\n"
            "    print('======================================================================')\n"
            "    print('🎮 LIVE 2.4GHz GAMEPAD PACKET SNIFFER ACTIVE (Channel %d)' % ch)\n"
            "    print('   Listening for wireless controller packets for %.1f seconds...' % duration_sec)\n"
            "    print('======================================================================\\n')\n"
            "    start = time.time()\n"
            "    count = 0; last_hex = ''\n"
            "    while time.time() - start < duration_sec:\n"
            "        st = r_reg(0x07); fifo = r_reg(0x17)\n"
            "        if (st & 0x40) or ((fifo & 0x01) == 0):\n"
            "            payload = r_payload(16)\n"
            "            hex_str = ' '.join(['%02X' % b for b in payload])\n"
            "            if hex_str != last_hex:\n"
            "                count += 1\n"
            "                bin_bits = ' '.join(['{:08b}'.format(b) for b in payload[:4]])\n"
            "                print('FRAME #%03d | HEX: [%s]' % (count, hex_str))\n"
            "                print('          | BITS: %s' % bin_bits)\n"
            "                last_hex = hex_str\n"
            "            w_reg(0x07, 0x40)\n"
            "        time.sleep_ms(5)\n"
            "    ce.value(0)\n"
            "    print('\\n======================================================================')\n"
            "    print('Sniffing finished. Total unique payload state frames captured: %d' % count)\n"
            "sniff_gamepad_packets(2, 2.5)\n"
        )
    },
    "promiscuous": {
        "title": "🕵️ Universal Promiscuous Preamble Sniffer (FHSS Hopping)",
        "desc": "Disables CRC, sets 2-byte 0x55 0x55 preamble matching, & hops across channels [10, 25, 38, 48, 64, 76] to intercept FHSS controllers.",
        "script": (
            "import machine, time\n"
            "def promiscuous_hop_sniff(channels=[10, 25, 38, 48, 64, 76], duration_sec=3.0, data_rate_mode='1M'):\n"
            "    sck = machine.Pin(14, machine.Pin.OUT)\n"
            "    mosi = machine.Pin(13, machine.Pin.OUT)\n"
            "    miso = machine.Pin(12, machine.Pin.IN)\n"
            "    csn = machine.Pin(15, machine.Pin.OUT, value=1)\n"
            "    ce = machine.Pin(16, machine.Pin.OUT, value=0)\n"
            "    try: machine.SPI(1).deinit()\n"
            "    except Exception: pass\n"
            "    spi = machine.SPI(1, baudrate=4000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "    def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)\n"
            "    def w_buf(r, buf): csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)\n"
            "    def r_reg(r): csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]\n"
            "    def r_payload(l=16): csn.value(0); rx = spi.read(l + 1, 0x61); csn.value(1); return rx[1:]\n"
            "    ce.value(0)\n"
            "    w_reg(0x00, 0x03) # PWR_UP=1, PRIM_RX=1, NO_CRC\n"
            "    w_reg(0x01, 0x00) # Disable Auto-ACK\n"
            "    w_reg(0x02, 0x01) # Enable Pipe 0\n"
            "    w_reg(0x03, 0x00) # 2-byte Preamble Match Address Width\n"
            "    rf_setup = 0x07 if data_rate_mode == '1M' else 0x0F\n"
            "    w_reg(0x06, rf_setup)\n"
            "    w_reg(0x11, 16)\n"
            "    w_buf(0x0A, b'\\x55\\x55')\n"
            "    w_reg(0x07, 0x70)\n"
            "    csn.value(0); spi.write(bytes([0xE2])); csn.value(1)\n"
            "    ce.value(1)\n"
            "    print('======================================================================')\n"
            "    print('🕵️ UNIVERSAL PROMISCUOUS PREAMBLE SNIFFER ACTIVE (%s)' % data_rate_mode)\n"
            "    print('   Hopping Channels: %s | Preamble Match: 0x55 0x55 | CRC: OFF' % str(channels))\n"
            "    print('   PRESS AND HOLD GAMEPAD BUTTONS NOW!')\n"
            "    print('======================================================================\\n')\n"
            "    start = time.time(); count = 0; last_hex = ''\n"
            "    while time.time() - start < duration_sec:\n"
            "        for ch in channels:\n"
            "            w_reg(0x05, ch)\n"
            "            time.sleep_ms(8)\n"
            "            st = r_reg(0x07); fifo = r_reg(0x17)\n"
            "            if (st & 0x40) or ((fifo & 0x01) == 0):\n"
            "                payload = r_payload(16)\n"
            "                hex_str = ' '.join(['%02X' % b for b in payload])\n"
            "                if hex_str != last_hex and payload != bytes(16) and payload != b'\\xFF'*16:\n"
            "                    count += 1\n"
            "                    bin_bits = ' '.join(['{:08b}'.format(b) for b in payload[:4]])\n"
            "                    print('FRAME #%03d [CH %2d] | HEX: [%s]' % (count, ch, hex_str))\n"
            "                    print('                         | BITS: %s' % bin_bits)\n"
            "                    last_hex = hex_str\n"
            "                w_reg(0x07, 0x40)\n"
            "    ce.value(0)\n"
            "    print('\\nPromiscuous Sniffing Complete. Total valid frames captured: %d' % count)\n"
            "promiscuous_hop_sniff([10, 25, 38, 48, 64, 76], 3.0, '1M')\n"
        )
    },
    "isolator": {
        "title": "🔬 Gamepad Differential Signal Isolator",
        "desc": "Runs a 2-phase test comparing ambient Wi-Fi/BT baseline noise against active button press bursts to pinpoint the exact gamepad channel & payload.",
        "script": (
            "import machine, time\n"
            "def run_isolation(channels=[10, 25, 38, 48, 58, 64, 76]):\n"
            "    sck = machine.Pin(14, machine.Pin.OUT)\n"
            "    mosi = machine.Pin(13, machine.Pin.OUT)\n"
            "    miso = machine.Pin(12, machine.Pin.IN)\n"
            "    csn = machine.Pin(15, machine.Pin.OUT, value=1)\n"
            "    ce = machine.Pin(16, machine.Pin.OUT, value=0)\n"
            "    try: machine.SPI(1).deinit()\n"
            "    except Exception: pass\n"
            "    spi = machine.SPI(1, baudrate=4000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
            "    def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)\n"
            "    def w_buf(r, buf): csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)\n"
            "    def r_reg(r): csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]\n"
            "    def r_payload(l=32): csn.value(0); rx = spi.read(l + 1, 0x61); csn.value(1); return rx[1:]\n"
            "    def config_rx(ch):\n"
            "        ce.value(0)\n"
            "        w_reg(0x00, 0x03); w_reg(0x01, 0x00); w_reg(0x02, 0x01); w_reg(0x03, 0x01)\n"
            "        w_reg(0x06, 0x0F); w_reg(0x11, 32); w_buf(0x0A, b'\\x55\\x55\\x55'); w_reg(0x05, ch)\n"
            "        w_reg(0x07, 0x70)\n"
            "        csn.value(0); spi.write(bytes([0xE2])); csn.value(1)\n"
            "        ce.value(1)\n"
            "    print('======================================================================')\n"
            "    print('🔬 STEP 1: BASELINE AMBIENT NOISE SCAN (1.5 SECONDS)')\n"
            "    print('👉 KEEP GAMEPAD IDLE! DO NOT TOUCH BUTTONS YET.')\n"
            "    print('======================================================================\\n')\n"
            "    base_counts = {}\n"
            "    for ch in channels:\n"
            "        config_rx(ch)\n"
            "        t0 = time.time(); cnt = 0\n"
            "        while time.time() - t0 < 0.2:\n"
            "            st = r_reg(0x07); fifo = r_reg(0x17)\n"
            "            if (st & 0x40) or ((fifo & 0x01) == 0): cnt += 1; w_reg(0x07, 0x40)\n"
            "            time.sleep_ms(2)\n"
            "        base_counts[ch] = cnt\n"
            "        print('   Ch %2d (2.%03d GHz) Idle Noise: %d pkts' % (ch, 400+ch, cnt))\n"
            "    print('\\n======================================================================')\n"
            "    print('🔬 STEP 2: ACTIVE CONTROLLER BURST SCAN (1.5 SECONDS)')\n"
            "    print('👉 PRESS AND HOLD A BUTTON / JOYSTICK NOW!')\n"
            "    print('======================================================================\\n')\n"
            "    time.sleep(0.5)\n"
            "    active_counts = {}; samples = []\n"
            "    for ch in channels:\n"
            "        config_rx(ch)\n"
            "        t0 = time.time(); cnt = 0\n"
            "        while time.time() - t0 < 0.25:\n"
            "            st = r_reg(0x07); fifo = r_reg(0x17)\n"
            "            if (st & 0x40) or ((fifo & 0x01) == 0):\n"
            "                p = r_payload(32); cnt += 1\n"
            "                if p != bytes(32) and p != b'\\xFF'*32:\n"
            "                    hex_str = ' '.join(['%02X' % b for b in p[:12]])\n"
            "                    samples.append((ch, hex_str))\n"
            "                w_reg(0x07, 0x40)\n"
            "            time.sleep_ms(2)\n"
            "        active_counts[ch] = cnt\n"
            "    print('--- DIFFERENTIAL SURGE ANALYSIS ---')\n"
            "    best_ch = -1; max_surge = 0\n"
            "    for ch in channels:\n"
            "        b = base_counts.get(ch, 0); a = active_counts.get(ch, 0); surge = a - b\n"
            "        print('Ch %2d | Idle: %2d | Active: %2d | SURGE: %+2d' % (ch, b, a, surge))\n"
            "        if surge > max_surge:\n"
            "            max_surge = surge; best_ch = ch\n"
            "    if best_ch != -1 and max_surge >= 3:\n"
            "        print('\\n🎉 GAMEPAD CHANNEL ISOLATED: Channel %d!' % best_ch)\n"
            "        print('   Payload sample on Channel %d:' % best_ch)\n"
            "        for c, h in samples:\n"
            "            if c == best_ch:\n"
            "                print('   -> HEX: [%s]' % h)\n"
            "    else:\n"
            "        print('\\n⚠️ No high burst surge above baseline noise. Retry with button held down!')\n"
            "run_isolation([10, 25, 38, 48, 58, 64, 76])\n"
        )
    },
    "gc": {
        "title": "🧹 Memory Garbage Collector & Trim",
        "desc": "Forces Python garbage collection and reports reclaimed memory heap space.",
        "script": (
            "import gc\n"
            "before = gc.mem_free()\n"
            "gc.collect()\n"
            "after = gc.mem_free()\n"
            "print('Garbage Collection complete. Reclaimed:', after - before, 'bytes.')\n"
            "print('Current Free RAM Heap:', after, 'bytes.')\n"
            "print('Free RAM Heap:', after)\n"
        )
    }
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ ESP32 Retro Control Center & Live Code Inspector</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0b0d17 0%, #151828 50%, #080911 100%);
            --card-bg: rgba(22, 27, 44, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --accent-purple: #9d50bb;
            --accent-emerald: #10b981;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container { width: 100%; max-width: 760px; }
        header { text-align: center; margin-bottom: 24px; }

        .logo-badge {
            display: inline-block;
            background: linear-gradient(90deg, #00f2fe, #4facfe);
            color: #0b0d17;
            font-weight: 700;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            padding: 4px 14px;
            border-radius: 20px;
            margin-bottom: 8px;
        }

        h1 {
            font-size: 1.85rem;
            font-weight: 700;
            background: linear-gradient(90deg, #ffffff, var(--accent-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p.subtitle { color: var(--text-muted); font-size: 0.9rem; margin-top: 4px; }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .select-box {
            width: 100%;
            background: #0d101d;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            color: #38bdf8;
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            padding: 12px;
            margin-bottom: 12px;
        }

        .preset-desc-box {
            background: rgba(0, 0, 0, 0.3);
            border-left: 3px solid var(--accent-cyan);
            padding: 10px 14px;
            font-size: 0.85rem;
            color: var(--text-muted);
            border-radius: 4px;
            margin-bottom: 12px;
        }

        .code-box-header {
            font-size: 0.8rem;
            color: var(--accent-cyan);
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .btn {
            background: linear-gradient(135deg, rgba(79, 172, 254, 0.15) 0%, rgba(0, 242, 254, 0.15) 100%);
            border: 1px solid rgba(0, 242, 254, 0.3);
            color: var(--text-main);
            padding: 14px 16px;
            border-radius: 12px;
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
            text-align: center;
        }

        .btn:hover {
            background: linear-gradient(135deg, rgba(79, 172, 254, 0.3) 0%, rgba(0, 242, 254, 0.3) 100%);
            border-color: var(--accent-cyan);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 242, 254, 0.25);
        }

        .btn-purple {
            background: linear-gradient(135deg, rgba(157, 80, 187, 0.2) 0%, rgba(110, 72, 170, 0.2) 100%);
            border-color: rgba(157, 80, 187, 0.4);
        }

        .btn-purple:hover {
            background: linear-gradient(135deg, rgba(157, 80, 187, 0.4) 0%, rgba(110, 72, 170, 0.4) 100%);
            border-color: var(--accent-purple);
            box-shadow: 0 6px 20px rgba(157, 80, 187, 0.3);
        }

        .btn-full { grid-column: span 2; width: 100%; margin-top: 10px; }
        .btn-icon { font-size: 1.3rem; }

        .terminal-box {
            background: #05060a;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            color: #38bdf8;
            height: 250px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .log-entry { margin-bottom: 4px; line-height: 1.4; }
        .log-time { color: var(--text-muted); }
        .log-success { color: #34d399; }
        .log-info { color: #60a5fa; }
        .log-err { color: #f87171; }

        .code-input-box {
            width: 100%;
            background: #060810;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            color: #38bdf8;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            padding: 12px;
            line-height: 1.4;
            resize: vertical;
        }

        .status-dot {
            width: 8px; height: 8px; border-radius: 50%; background: #10b981;
            display: inline-block; box-shadow: 0 0 10px #10b981;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-badge"><span class="status-dot"></span> ESP32 USB OTG AUTO-DETECT ACTIVE</div>
            <h1>Retro Hardware Control & Live Code Inspector</h1>
            <p class="subtitle">Pixel 8 Pro Engine & Fine Granular MicroPython Exposer</p>
        </header>

        <div class="card">
            <div class="card-title">🎛️ Fine Granular Hardware Presets</div>
            <select id="presetSelect" class="select-box" onchange="updatePresetView()">
                <option value="blink">🔵 Blink Blue LED (GPIO2)</option>
                <option value="specs">🧠 Full SoC & System Diagnostics</option>
                <option value="sensors">🌡️ Internal Thermal & ADC Telemetry</option>
                <option value="probe_gpios">⚡ Universal GPIO Pin Inspector & Electrical Prober</option>
                <option value="storage">💾 Flash Storage & File System</option>
                <option value="clock_240">⚡ Set CPU Frequency to 240 MHz</option>
                <option value="clock_160">🌿 Set CPU Frequency to 160 MHz</option>
                <option value="spi_scan">📡 NRF24 SPI Register Matrix Dump</option>
                <option value="auto_discover">🔍 Auto-Discover NRF24 SPI Pins</option>
                <option value="rf_sweep">📶 2.4GHz RF Carrier Sweeper</option>
                <option value="sniffer">🕵️ 2.4GHz Promiscuous Sniffer Setup Mode</option>
                <option value="sniffer_live">🎮 Live 2.4GHz Gamepad Packet Sniffer & Logger</option>
                <option value="promiscuous">🕵️ Universal Promiscuous Preamble Sniffer (FHSS Hopping)</option>
                <option value="isolator">🔬 Gamepad Differential Signal Isolator</option>
                <option value="gc">🧹 Memory Garbage Collector & Trim</option>
            </select>
            
            <div class="preset-desc-box" id="presetDesc">
                Pulses the onboard blue LED 5 times at 300ms intervals.
            </div>

            <div class="code-box-header">
                <span>🐍 Executable MicroPython Device Code</span>
                <span style="color: #94a3b8; font-weight: 400; text-transform: none;">Sent live over USB OTG</span>
            </div>
            <textarea id="presetScriptCode" class="code-input-box" rows="6" readonly></textarea>

            <button class="btn btn-full" onclick="executeSelectedPreset()">
                <span class="btn-icon">⚡</span>
                <span>Execute Preset on ESP32</span>
            </button>
        </div>

        <div class="card">
            <div class="card-title">🐍 Live Custom MicroPython Code Injector</div>
            <textarea id="pythonCode" class="code-input-box" rows="4" placeholder="Type any custom MicroPython script (e.g. import machine; print(machine.freq()))"></textarea>
            <button class="btn btn-purple btn-full" onclick="injectCustomCode()">
                <span class="btn-icon">▶️</span>
                <span>Execute Custom Code on ESP32</span>
            </button>
        </div>

        <div class="card">
            <div class="card-title">💻 Live Hardware Console Stream</div>
            <div class="terminal-box" id="terminal">Auto-Detection Engine Ready. USB OTG Host link monitoring active...\n</div>
        </div>
    </div>

    <script>
        const presetData = """ + json.dumps(PRESETS) + """;

        function updatePresetView() {
            const val = document.getElementById('presetSelect').value;
            const item = presetData[val];
            if (item) {
                document.getElementById('presetDesc').innerText = item.desc;
                document.getElementById('presetScriptCode').value = item.script;
                // Also copy to custom code injector for quick editing
                document.getElementById('pythonCode').value = item.script;
            }
        }

        function logToTerm(text, type = 'info') {
            const term = document.getElementById('terminal');
            const time = new Date().toLocaleTimeString();
            const colorClass = type === 'success' ? 'log-success' : type === 'err' ? 'log-err' : 'log-info';
            term.innerHTML += `<div class="log-entry"><span class="log-time">[${time}]</span> <span class="${colorClass}">${escapeHtml(text)}</span></div>`;
            term.scrollTop = term.scrollHeight;
        }

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        async function executeSelectedPreset() {
            const presetKey = document.getElementById('presetSelect').value;
            logToTerm(`Executing Preset Facility: [${presetKey}]...`, 'info');
            try {
                const response = await fetch(`/api/command?type=${presetKey}`);
                const data = await response.json();
                if (data.success) {
                    logToTerm(`Execution Result:\n${data.output}`, 'success');
                } else {
                    logToTerm(`Error: ${data.error}`, 'err');
                }
            } catch (err) {
                logToTerm(`Network Exception: ${err.message}`, 'err');
            }
        }

        async function injectCustomCode() {
            const code = document.getElementById('pythonCode').value;
            if (!code.trim()) return;
            logToTerm(`Injecting MicroPython Code:\n${code}`, 'info');
            try {
                const response = await fetch('/api/custom_eval', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: code})
                });
                const data = await response.json();
                if (data.success) {
                    logToTerm(`Output:\n${data.output}`, 'success');
                } else {
                    logToTerm(`Error: ${data.error}`, 'err');
                }
            } catch (err) {
                logToTerm(`Exception: ${err.message}`, 'err');
            }
        }

        // Initialize default view on load
        window.onload = updatePresetView;
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        elif self.path.startswith("/api/command"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            cmd_type = "blink"
            for param in query.split("&"):
                if param.startswith("type="):
                    cmd_type = param.split("=", 1)[1]

            if cmd_type in PRESETS:
                script = PRESETS[cmd_type]["script"]
            else:
                script = "print('Unknown preset command')"

            try:
                res = run_micropython_script(script)
            except Exception as e:
                res = {"success": False, "error": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif self.path == "/api/diagnostics":
            dev = auto_detect_usb_device()
            diag = {
                "usb_detected": dev is not None,
                "usb_device": "Silicon Labs CP2102 (0x10c4:0xea60)" if dev else "Disconnected",
                "presets_available": list(PRESETS.keys()),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(diag).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/custom_eval":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                code = data.get('code', '')
                res = run_micropython_script(code)
            except Exception as e:
                res = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

def main():
    port = 8080
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"==================================================", flush=True)
    print(f"🚀 ESP32 Control Center & Live Code Inspector Active!", flush=True)
    print(f"   URL: http://localhost:{port}", flush=True)
    print(f"==================================================", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")

if __name__ == '__main__':
    main()
