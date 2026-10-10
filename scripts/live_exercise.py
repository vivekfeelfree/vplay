#!/data/data/com.termux/files/usr/bin/python3
"""
🎮 Live 2.4GHz Gamepad RF Interception & Framing Exercise Engine
Runs a multi-phase diagnostic directly on ESP32 over USB OTG to pinpoint the exact 
RF channel, address framing, bit rate, and raw packet payloads from the retro controller.
"""

import sys
import time
import struct
import usb.core
import usb.backend.libusb1 as libusb1

REQTYPE_HOST_TO_INTERFACE = 0x41
CP210X_IFC_ENABLE = 0x00
CP210X_SET_BAUD   = 0x1E
CP210X_SET_LINE   = 0x03
CP210X_SET_MHS    = 0x07

LIVE_EXERCISE_MICROPYTHON = """
import machine, time

def run_live_rf_exercise():
    sck = machine.Pin(14, machine.Pin.OUT)
    mosi = machine.Pin(13, machine.Pin.OUT)
    miso = machine.Pin(12, machine.Pin.IN)
    csn = machine.Pin(15, machine.Pin.OUT, value=1)
    ce = machine.Pin(16, machine.Pin.OUT, value=0)

    try: machine.SPI(1).deinit()
    except Exception: pass
    spi = machine.SPI(1, baudrate=4000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

    def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)
    def w_buf(r, buf): csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)
    def r_reg(r): csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]
    def r_payload(l=32): csn.value(0); rx = spi.read(l + 1, 0x61); csn.value(1); return rx[1:]

    print("======================================================================")
    print("📡 LIVE EXERCISE PHASE 1: REAL-TIME CARRIER SPECTRUM SCANNER (8 sec)")
    print("👉 ACTION REQUIRED: PRESS AND HOLD 'DOWN' OR 'A' BUTTON CONTINUOUSLY!")
    print("======================================================================\\n")

    ce.value(0)
    w_reg(0x00, 0x0F) # PWR_UP, PRIM_RX
    w_reg(0x01, 0x00) # Disable Auto-ACK
    w_reg(0x02, 0x01) # Enable Pipe 0
    w_reg(0x03, 0x03) # 5-byte address width
    w_reg(0x06, 0x0F) # 2Mbps
    ce.value(1)

    rpd_counts = {}
    scan_start = time.time()
    
    while time.time() - scan_start < 8.0:
        for ch in range(0, 81, 2):
            w_reg(0x05, ch)
            time.sleep_us(250)
            rpd = r_reg(0x09) & 0x01
            st = r_reg(0x07)
            if rpd or (st & 0x40):
                rpd_counts[ch] = rpd_counts.get(ch, 0) + 1
                w_reg(0x07, 0x40)

    print("--- SPECTRUM CARRIER SCAN RESULTS ---")
    if not rpd_counts:
        print("⚠️ No RF carrier bursts detected! Using fallback channels [10, 25, 38, 48, 64, 76]")
        active_channels = [38, 48, 10, 25, 64, 76]
    else:
        sorted_chs = sorted(rpd_counts.items(), key=lambda x: x[1], reverse=True)
        print("Detected RF Carrier Activity on Channels:")
        for ch, cnt in sorted_chs[:6]:
            bar = "#" * min(cnt, 25)
            print("  Channel %2d (2.%03d GHz) : %-25s (%d bursts)" % (ch, 400 + ch, bar, cnt))
        active_channels = [ch for ch, _ in sorted_chs[:6]]

    print("\\n======================================================================")
    print("🕵️ LIVE EXERCISE PHASE 2: MULTI-ADDRESS & RATE PROMISCUOUS MATRIX SCAN")
    print("👉 ACTION REQUIRED: KEEP PRESSING BUTTONS (A, B, D-PAD) ON GAMEPAD!")
    print("======================================================================\\n")

    matrix_configs = [
        ("1M-Preamble-55", 0x07, 0x01, b'\\x55\\x55\\x55', 0x03),
        ("2M-Preamble-55", 0x0F, 0x01, b'\\x55\\x55\\x55', 0x03),
        ("1M-Preamble-AA", 0x07, 0x01, b'\\xAA\\xAA\\xAA', 0x03),
        ("2M-Preamble-AA", 0x0F, 0x01, b'\\xAA\\xAA\\xAA', 0x03),
        ("1M-NullAddr-00", 0x07, 0x03, b'\\x00\\x00\\x00\\x00\\x00', 0x03),
        ("2M-NullAddr-00", 0x0F, 0x03, b'\\x00\\x00\\x00\\x00\\x00', 0x03),
        ("1M-LT8920-Def",  0x07, 0x03, b'\\x61\\x62\\x63\\x64\\x65', 0x03),
        ("2M-Retro-ASIC",  0x0F, 0x03, b'\\x34\\x43\\x10\\x10\\x01', 0x03),
        ("1M-CRC-Default", 0x07, 0x03, b'\\xE7\\xE7\\xE7\\xE7\\xE7', 0x0F),
    ]

    captured_frames = []

    for label, rf_setup, aw, addr_buf, cfg in matrix_configs:
        print("Testing Matrix Config [%-15s] on channels %s..." % (label, str(active_channels)))
        ce.value(0)
        w_reg(0x00, cfg) # Config
        w_reg(0x01, 0x00) # No ACK
        w_reg(0x02, 0x01) # Pipe 0
        w_reg(0x03, aw)   # Address width
        w_reg(0x06, rf_setup)
        w_reg(0x11, 32)   # 32-byte payload
        w_buf(0x0A, addr_buf)
        w_reg(0x07, 0x70)
        csn.value(0); spi.write(bytes([0xE2])); csn.value(1) # FLUSH_RX
        ce.value(1)

        t0 = time.time()
        while time.time() - t0 < 1.2:
            for ch in active_channels:
                w_reg(0x05, ch)
                time.sleep_ms(6)
                st = r_reg(0x07)
                fifo = r_reg(0x17)
                if (st & 0x40) or ((fifo & 0x01) == 0):
                    p = r_payload(32)
                    hex_str = ' '.join(['%02X' % b for b in p[:16]])
                    if p != bytes(32) and p != b'\\xFF'*32:
                        print("  🎉 [SUCCESS] CAPTURED FRAME with [%s] on CH %d!" % (label, ch))
                        print("      HEX: [%s]" % hex_str)
                        print("      BITS: %s" % ' '.join(['{:08b}'.format(b) for b in p[:4]]))
                        captured_frames.append((label, ch, hex_str))
                    w_reg(0x07, 0x40)

    ce.value(0)
    print("\\n======================================================================")
    print("🏆 LIVE EXERCISE RESULTS SUMMARY")
    print("======================================================================")
    if captured_frames:
        print("SUCCESS! Captured %d wireless gamepad frames over the air!" % len(captured_frames))
        for item in captured_frames:
            print(" -> Config: %s | Channel: %d | Hex: %s" % item)
    else:
        print("⚠️ No direct frames matched standard preambles.")
        print("👉 Recommended next action: Inspect chip marking on gamepad receiver/stick!")
        print("   If controller uses bit-scrambled XN297 format, we will load XN297 software descrambler!")

run_live_rf_exercise()
"""

def execute_live_exercise():
    backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
    dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60, backend=backend)
    
    if dev is None:
        print("❌ Error: ESP32 board (CP2102) not found on USB OTG.")
        return

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
        dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, (0x03 << 8) | 0x00, 0, None)
        time.sleep(0.1)

        # Interrupt REPL and send MicroPython payload
        dev.write(0x01, b'\x03\x03\r\n', timeout=1000)
        time.sleep(0.2)

        print("Executing Live Exercise MicroPython Script on ESP32...", flush=True)
        script_bytes = LIVE_EXERCISE_MICROPYTHON.encode('utf-8')
        
        # Send line by line to REPL
        for line in script_bytes.split(b'\n'):
            dev.write(0x01, line + b'\r\n', timeout=1000)
            time.sleep(0.01)

        start_time = time.time()
        while time.time() - start_time < 25.0:
            try:
                rx = dev.read(0x81, 256, timeout=100)
                if rx:
                    out = bytes(rx).decode('utf-8', errors='replace')
                    sys.stdout.write(out)
                    sys.stdout.flush()
            except usb.core.USBTimeoutError:
                pass
            except Exception:
                pass
    except usb.core.USBError as e:
        if e.errno == 16 or "Resource busy" in str(e):
            print("❌ USB port locked by background process. Please stop web server first or run via web server.")
        else:
            raise e

if __name__ == '__main__':
    execute_live_exercise()
