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

def main():
    print("=== Testing ESP32 Auto-Reset to Download Mode ===")
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

    # Trigger ESP32 Bootloader Sequence:
    # 1. DTR=1 (GPIO0=LOW), RTS=1 (EN=LOW) -> Chip Reset with GPIO0 LOW
    wValue = (0x03 << 8) | 0x03
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, wValue, 0, None)
    time.sleep(0.1)

    # 2. DTR=1 (GPIO0=LOW), RTS=0 (EN=HIGH) -> Chip comes out of reset into Download Mode
    wValue = (0x03 << 8) | 0x01
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, wValue, 0, None)
    time.sleep(0.1)

    # 3. DTR=0 (GPIO0=HIGH), RTS=0 (EN=HIGH) -> Normal operation release
    wValue = (0x03 << 8) | 0x00
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, wValue, 0, None)
    time.sleep(0.2)

    print("Reading ESP32 Download Mode Boot response...")
    boot_buf = bytearray()
    start = time.time()
    while time.time() - start < 2.0:
        try:
            data = dev.read(0x81, 64, timeout=50)
            if data:
                boot_buf.extend(data)
        except Exception:
            pass

    print(f"Read {len(boot_buf)} bytes.")
    if boot_buf:
        print("--- ESP32 Download Mode Log ---")
        clean_hex = ' '.join([f"{b:02x}" for b in boot_buf[:50]])
        print("First 50 Hex Bytes:", clean_hex)
        ascii_text = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in boot_buf])
        print("Sanitized Text:", ascii_text[:200])
        print("-------------------------------")

if __name__ == '__main__':
    main()
