#!/data/data/com.termux/files/usr/bin/python3
import os
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

def scan_spi():
    print("==================================================", flush=True)
    print("📡 Milestone 3: NRF24L01+/Si24R1 SPI Bus Diagnostic", flush=True)
    print("   Target Pins: SCK=18, MOSI=23, MISO=19, CSN=5, CE=4", flush=True)
    print("==================================================\n", flush=True)

    backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
    dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60, backend=backend)
    
    if dev is None:
        print("❌ ESP32 board (CP2102) not found.")
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

    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_IFC_ENABLE, 0x0001, 0, None)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_LINE, 0x0800, 0, None)

    baud_bytes = struct.pack('<I', 115200)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_BAUD, 0, 0, baud_bytes)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, (0x03 << 8) | 0x00, 0, None)
    time.sleep(0.2)

    # Enter MicroPython Raw REPL Mode (Ctrl+C twice, then Ctrl+A)
    dev.write(0x01, b'\x03\x03\x01', timeout=1000)
    time.sleep(0.1)

    script = (
        "import machine, time\n"
        "sck = machine.Pin(18, machine.Pin.OUT)\n"
        "mosi = machine.Pin(23, machine.Pin.OUT)\n"
        "miso = machine.Pin(19, machine.Pin.IN)\n"
        "csn = machine.Pin(5, machine.Pin.OUT, value=1)\n"
        "ce = machine.Pin(4, machine.Pin.OUT, value=0)\n"
        "spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)\n"
        "def read_reg(reg):\n"
        "    csn.value(0)\n"
        "    res = spi.read(2, reg & 0x1F)\n"
        "    csn.value(1)\n"
        "    return res[1]\n"
        "def read_bytes(reg, length):\n"
        "    csn.value(0)\n"
        "    tx = bytes([reg & 0x1F]) + bytes(length)\n"
        "    rx = spi.read(length + 1, tx[0])\n"
        "    csn.value(1)\n"
        "    return rx[1:]\n"
        "print('=== NRF24L01+ / SI24R1 REGISTER DUMP ===')\n"
        "regs = [('CONFIG', 0x00), ('EN_AA', 0x01), ('EN_RXADDR', 0x02), ('SETUP_AW', 0x03), ('SETUP_RETR', 0x04), ('RF_CH', 0x05), ('RF_SETUP', 0x06), ('STATUS', 0x07)]\n"
        "for name, addr in regs:\n"
        "    val = read_reg(addr)\n"
        "    print('  %s (0x%02X): 0x%02X (bin: %s)' % (name, addr, val, bin(val)))\n"
        "tx_addr = read_bytes(0x10, 5)\n"
        "print('  TX_ADDR (0x10): %s' % (' '.join(['0x%02X' % b for b in tx_addr])))\n"
    )
    
    # Send script bytes + Ctrl+D to execute
    dev.write(0x01, script.encode('utf-8') + b'\x04', timeout=1000)
    
    print("Reading SPI Register Scan results from ESP32...", flush=True)
    start = time.time()
    out = bytearray()
    while time.time() - start < 4.0:
        try:
            chunk = dev.read(0x81, 128, timeout=50)
            if chunk:
                out.extend(chunk)
        except Exception:
            pass

    raw_text = out.decode('utf-8', errors='replace')
    print("---------------- MicroPython Output ----------------")
    print(raw_text)
    print("--------------------------------------------------")

if __name__ == '__main__':
    scan_spi()
