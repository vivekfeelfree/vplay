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

def blink_led():
    print("=== Executing MicroPython Code: Blinking Onboard Blue LED (GPIO2) ===", flush=True)
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

    # Release reset (RTS=0, DTR=0)
    dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, (0x03 << 8) | 0x00, 0, None)
    time.sleep(0.2)

    # Enter MicroPython Raw REPL Mode (Ctrl+A)
    dev.write(0x01, b'\x03\x03\x01', timeout=1000)
    time.sleep(0.1)

    script = (
        "import machine, time\n"
        "led = machine.Pin(2, machine.Pin.OUT)\n"
        "for i in range(5):\n"
        "    led.value(1)\n"
        "    print('LED IS ON [BLUE HIGH]')\n"
        "    time.sleep(0.4)\n"
        "    led.value(0)\n"
        "    print('LED IS OFF [BLUE LOW]')\n"
        "    time.sleep(0.4)\n"
    )
    
    # Send script bytes + Ctrl+D to execute
    dev.write(0x01, script.encode('utf-8') + b'\x04', timeout=1000)
    
    print("Reading live output from ESP32 MicroPython script...", flush=True)
    start = time.time()
    out = bytearray()
    while time.time() - start < 5.0:
        try:
            chunk = dev.read(0x81, 64, timeout=50)
            if chunk:
                out.extend(chunk)
        except Exception:
            pass

    print("---------------- MicroPython Output ----------------")
    print(out.decode('utf-8', errors='replace'))
    print("--------------------------------------------------")

if __name__ == '__main__':
    blink_led()
