#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import struct
import usb.core
import usb.backend.libusb1 as libusb1

# CP2102 USB Control Request Constants
REQTYPE_HOST_TO_INTERFACE = 0x41
REQTYPE_HOST_TO_DEVICE    = 0x40

CP210X_IFC_ENABLE = 0x00
CP210X_SET_BAUD   = 0x1E
CP210X_SET_LINE   = 0x03
CP210X_SET_MHS    = 0x07

def test_cp2102():
    print("=== Testing CP2102 USB-to-UART Bridge Communication ===")
    
    backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
    dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60, backend=backend)
    
    if dev is None:
        print("Error: CP2102 device not found.")
        return
        
    print(f"Device found: {hex(dev.idVendor)}:{hex(dev.idProduct)}")
    
    # Detach kernel driver if active
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception as e:
        print(f"Kernel driver check: {e}")
        
    # Set configuration
    try:
        dev.set_configuration()
    except Exception as e:
        print(f"Set configuration note: {e}")

    # Enable Interface
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_IFC_ENABLE, 0x0001, 0, None)
    
    # Set Baud Rate to 74880 (ESP32 ROM bootloader default)
    baudrate = 74880
    baud_bytes = struct.pack('<I', baudrate)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_BAUD, 0, 0, baud_bytes)
    print(f"Set Baudrate to {baudrate} baud.")
    
    # Set Line Control 8N1 (0x0800)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_LINE, 0x0800, 0, None)
    
    # Pulse EN/GPIO0 to Reset ESP32:
    # EN (Reset) = RTS pin, GPIO0 (Boot) = DTR pin
    print("Resetting ESP32 via RTS/DTR pins...")
    # Set RTS=1 (EN low), DTR=0
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, 0x0202, 0, None)
    time.sleep(0.1)
    # Set RTS=0 (EN high)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, 0x0100, 0, None)
    time.sleep(0.2)
    
    print("Reading serial boot logs from ESP32 for 3 seconds...")
    end_time = time.time() + 3.0
    boot_log = bytearray()
    
    while time.time() < end_time:
        try:
            # Read from Bulk IN Endpoint 0x81 (timeout 100ms)
            data = dev.read(0x81, 64, timeout=100)
            if data:
                boot_log.extend(data)
        except usb.core.USBTimeoutError:
            pass
        except Exception as e:
            print(f"Read error: {e}")
            break
            
    print(f"\nReceived {len(boot_log)} bytes from ESP32 serial tx:")
    if boot_log:
        try:
            text = boot_log.decode('utf-8', errors='replace')
            print("--- ESP32 Boot Output ---")
            print(text)
            print("-------------------------")
        except Exception as e:
            print(f"Hex output: {boot_log.hex()}")
    else:
        print("(No boot text received - will retry pulse)")

if __name__ == '__main__':
    test_cp2102()
