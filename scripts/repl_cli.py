#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import struct
import select
import usb.core
import usb.backend.libusb1 as libusb1

REQTYPE_HOST_TO_INTERFACE = 0x41
CP210X_IFC_ENABLE = 0x00
CP210X_SET_BAUD   = 0x1E
CP210X_SET_LINE   = 0x03
CP210X_SET_MHS    = 0x07

def main():
    print("==================================================", flush=True)
    print("🚀 Interactive MicroPython REPL Terminal over USB", flush=True)
    print("   Type any Python code and press Enter!")
    print("   Press Ctrl+C or type 'exit()' to return to shell.", flush=True)
    print("==================================================\n", flush=True)

    backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
    dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60, backend=backend)
    
    if dev is None:
        print("Error: ESP32 board (CP2102) not found.")
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

        # Wake up REPL with Ctrl+C + Enter
        dev.write(0x01, b'\x03\r\n', timeout=1000)
    except usb.core.USBError as e:
        if e.errno == 16 or "Resource busy" in str(e):
            print("\n❌ USB Device is currently locked by another process (e.g. web_server.py).", flush=True)
            print("👉 Please open http://localhost:8080 in your browser to use the interactive dashboard,", flush=True)
            print("   OR stop the background web server if you want to use this command-line REPL.\n", flush=True)
            return
        else:
            raise e

    try:
        while True:
            # Drain USB RX bytes and print them
            try:
                rx = dev.read(0x81, 128, timeout=20)
                if rx:
                    sys.stdout.write(bytes(rx).decode('utf-8', errors='replace'))
                    sys.stdout.flush()
            except usb.core.USBTimeoutError:
                pass
            except Exception:
                pass

            # Check for keyboard input non-blocking
            rlist, _, _ = select.select([sys.stdin], [], [], 0.02)
            if rlist:
                line = sys.stdin.readline()
                if not line or line.strip() == "exit()":
                    print("\nExiting REPL terminal...")
                    break
                dev.write(0x01, line.encode('utf-8'), timeout=1000)
    except KeyboardInterrupt:
        print("\nExiting REPL terminal...")

if __name__ == '__main__':
    main()
