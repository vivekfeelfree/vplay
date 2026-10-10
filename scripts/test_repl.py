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

def test_repl():
    print("=== Interacting with MicroPython REPL over USB OTG ===", flush=True)
    backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
    dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60, backend=backend)
    
    if dev is None:
        print("Device not found")
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

    # Enable IFC & set line 8N1
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_IFC_ENABLE, 0x0001, 0, None)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_LINE, 0x0800, 0, None)

    # Set baud rate 115200
    baud_bytes = struct.pack('<I', 115200)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_BAUD, 0, 0, baud_bytes)

    # Reset ESP32 into MicroPython execution mode:
    # Set RTS=1 (EN=LOW, chip in reset), DTR=0 (GPIO0=HIGH)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, (0x03 << 8) | 0x02, 0, None)
    time.sleep(0.1)
    # Set RTS=0 (EN=HIGH, chip boots MicroPython), DTR=0
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, (0x03 << 8) | 0x00, 0, None)
    time.sleep(0.5)

    # Drain buffer
    try:
        while True:
            dev.read(0x81, 64, timeout=10)
    except Exception:
        pass

    # Send Ctrl+C (Interrupt), Ctrl+D (Soft reset), and python commands
    print("Sending Ctrl+C and Python command to REPL...", flush=True)
    dev.write(0x01, b'\x03\x03\r\nimport sys, os; print("MICROPYTHON_PLATFORM:", sys.platform, "SYS_INFO:", sys.implementation); print("STORAGE_STAT:", os.statvfs("/")); \r\n', timeout=1000)
    
    time.sleep(0.5)
    
    repl_output = bytearray()
    start = time.time()
    while time.time() - start < 2.0:
        try:
            chunk = dev.read(0x81, 64, timeout=50)
            if chunk:
                repl_output.extend(chunk)
        except Exception:
            pass

    print(f"\nReceived {len(repl_output)} bytes from MicroPython REPL:")
    print("--------------------------------------------------")
    print(repl_output.decode('utf-8', errors='replace'))
    print("--------------------------------------------------")

if __name__ == '__main__':
    test_repl()
