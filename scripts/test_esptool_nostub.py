#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import struct
import usb.core
import usb.backend.libusb1 as libusb1
import esptool

REQTYPE_HOST_TO_INTERFACE = 0x41

CP210X_IFC_ENABLE = 0x00
CP210X_SET_BAUD   = 0x1E
CP210X_SET_LINE   = 0x03
CP210X_SET_MHS    = 0x07

class CP210xSerial:
    def __init__(self, vendor_id=0x10c4, product_id=0xea60):
        self.backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
        self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=self.backend)
        if self.dev is None:
            raise RuntimeError("CP2102 device not found")
            
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except Exception:
            pass
            
        try:
            self.dev.set_configuration()
        except Exception:
            pass
            
        self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_IFC_ENABLE, 0x0001, 0, None)
        self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_LINE, 0x0800, 0, None)
        
        self._baudrate = 115200
        self._dtr = False
        self._rts = False
        self.timeout = 0.5
        self.port = "CP2102_PyUSB"
        self.name = "CP2102_PyUSB"

    def isOpen(self):
        return True

    @property
    def is_open(self):
        return True

    def flushInput(self):
        self.reset_input_buffer()

    def flushOutput(self):
        self.reset_output_buffer()

    def inWaiting(self):
        return 0

    def outWaiting(self):
        return 0

    @property
    def in_waiting(self):
        return 0

    @property
    def out_waiting(self):
        return 0

    @property
    def baudrate(self):
        return self._baudrate
        
    @baudrate.setter
    def baudrate(self, baud):
        self._baudrate = baud
        baud_bytes = struct.pack('<I', baud)
        self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_BAUD, 0, 0, baud_bytes)

    def _update_mhs(self):
        val = (1 if self._dtr else 0) | (2 if self._rts else 0)
        mask = 0x03
        wValue = (mask << 8) | val
        self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, CP210X_SET_MHS, wValue, 0, None)

    def setDTR(self, level):
        self._dtr = bool(level)
        self._update_mhs()

    def setRTS(self, level):
        self._rts = bool(level)
        self._update_mhs()

    @property
    def dtr(self):
        return self._dtr
        
    @dtr.setter
    def dtr(self, value):
        self.setDTR(value)

    @property
    def rts(self):
        return self._rts
        
    @rts.setter
    def rts(self, value):
        self.setRTS(value)

    def write(self, data):
        if isinstance(data, (bytes, bytearray)):
            buf = data
        else:
            buf = bytes(data)
        if not buf:
            return 0
        written = self.dev.write(0x01, buf, timeout=1000)
        return written

    def read(self, size=1):
        result = bytearray()
        t = self.timeout if (self.timeout is not None and self.timeout > 0) else 0.05
        end_time = time.time() + t
        while len(result) < size:
            needed = size - len(result)
            try:
                chunk = self.dev.read(0x81, min(needed, 64), timeout=15)
                if chunk:
                    result.extend(chunk)
                elif time.time() >= end_time:
                    break
            except usb.core.USBTimeoutError:
                if time.time() >= end_time:
                    break
            except Exception:
                break
        return bytes(result)

    def flush(self):
        pass

    def reset_input_buffer(self):
        try:
            while True:
                self.dev.read(0x81, 64, timeout=5)
        except Exception:
            pass

    def reset_output_buffer(self):
        pass

    def close(self):
        pass

def main():
    print("=== Testing ROM Bootloader Direct Access (No Stub) ===", flush=True)
    port = CP210xSerial()
    
    # Pulse reset to enter download mode
    print("Resetting ESP32 into ROM Download mode...", flush=True)
    port.setDTR(True)
    port.setRTS(True)
    time.sleep(0.1)
    port.setRTS(False)
    time.sleep(0.1)
    port.setDTR(False)
    time.sleep(0.2)

    esp = esptool.detect_chip(port)
    print(f"Chip Identified: {esp.CHIP_NAME}", flush=True)
    
    mac = esp.read_mac()
    mac_str = ':'.join([f'{b:02x}' for b in mac])
    print(f"ESP32 MAC Address: {mac_str}", flush=True)
    
    print("Testing direct ROM flash_id command...", flush=True)
    flash_id = esp.flash_id()
    print(f"ESP32 Flash ID: 0x{flash_id:06x}", flush=True)
    print("SUCCESS: ROM Bootloader connection verified!", flush=True)

if __name__ == '__main__':
    main()
