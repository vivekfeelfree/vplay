#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import struct
import usb.core
import usb.backend.libusb1 as libusb1
import esptool

LOG_FILE = "/data/data/com.termux/files/home/trials/vplay/flasher_debug.log"

class TeeLogger:
    def __init__(self, filepath):
        self.file = open(filepath, "w", buffering=1)
        self.stdout = sys.__stdout__

    def write(self, data):
        self.stdout.write(data)
        self.stdout.flush()
        self.file.write(data)
        self.file.flush()

    def flush(self):
        self.stdout.flush()
        self.file.flush()

sys.stdout = TeeLogger(LOG_FILE)
sys.stderr = sys.stdout

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

REQTYPE_HOST_TO_INTERFACE = 0x41

CP210X_IFC_ENABLE = 0x00
CP210X_SET_BAUD   = 0x1E
CP210X_SET_LINE   = 0x03
CP210X_SET_MHS    = 0x07

class CP210xSerial:
    def __init__(self, vendor_id=0x10c4, product_id=0xea60):
        log("CP210xSerial: Initializing PyUSB backend...")
        self.backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
        self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=self.backend)
        if self.dev is None:
            raise RuntimeError("CP2102 device not found")
            
        try:
            self.dev.reset()
            time.sleep(0.2)
        except Exception:
            pass
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
        self.buffer = bytearray()
        log("CP210xSerial: Ready.")

    def isOpen(self):
        return True

    @property
    def is_open(self):
        return True

    def flushInput(self):
        self.buffer.clear()
        for _ in range(20):
            try:
                data = self.dev.read(0x81, 64, timeout=5)
                if not data:
                    break
            except Exception:
                break

    def flushOutput(self):
        pass

    def reset_input_buffer(self):
        self.buffer.clear()

    def reset_output_buffer(self):
        pass

    def inWaiting(self):
        return len(self.buffer)

    def outWaiting(self):
        return 0

    @property
    def in_waiting(self):
        return len(self.buffer)

    @property
    def out_waiting(self):
        return 0

    @property
    def baudrate(self):
        return self._baudrate
        
    @baudrate.setter
    def baudrate(self, baud):
        log(f"CP210xSerial: Setting baudrate to {baud}")
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
        if self.timeout is not None and self.timeout >= 10.0:
            t = max(self.timeout, 120.0)
        else:
            t = self.timeout if (self.timeout is not None and self.timeout > 0) else 0.2

        end_time = time.time() + t

        while len(self.buffer) < size and time.time() < end_time:
            try:
                chunk = self.dev.read(0x81, 64, timeout=20)
                if chunk:
                    self.buffer.extend(chunk)
            except usb.core.USBTimeoutError:
                pass
            except Exception:
                break
        res = bytes(self.buffer[:size])
        self.buffer = self.buffer[size:]
        return res

    def flush(self):
        pass

    def close(self):
        pass

def main():
    import traceback
    # Clear log
    with open(LOG_FILE, "w") as f:
        f.write("=== ESP32 Flasher Debug Log ===\n")
        
    log("Starting debug flasher...")
    try:
        port = CP210xSerial()
        
        log("Resetting ESP32 into download mode...")
        port.setDTR(True)
        port.setRTS(True)
        time.sleep(0.1)
        port.setRTS(False)
        time.sleep(0.1)
        port.setDTR(False)
        time.sleep(0.3)
        
        # Flush boot text output
        log("Flushing initial UART boot text...")
        port.flushInput()

        log("Detecting chip with esptool...")
        esp = esptool.detect_chip(port)
        log(f"CHIP DETECTED: {esp.CHIP_NAME}")
        
        log("Uploading RAM stub flasher...")
        esp = esp.run_stub()
        log("RAM Stub active!")
        
        mac = esp.read_mac()
        mac_str = ':'.join([f'{b:02x}' for b in mac])
        log(f"MAC ADDRESS: {mac_str}")
        
        flash_id = esp.flash_id()
        log(f"FLASH ID: 0x{flash_id:06x}")
        
        firmware_path = "ESP32_GENERIC-v1.22.2.bin"
        log(f"Flashing MicroPython image {firmware_path} at 0x1000 (4MB flash, flash_mode='keep')...")
        try:
            esp.change_baud(460800)
            log("High-speed baudrate 460800 active!")
        except Exception as e:
            log(f"Baudrate change note: {e}")
            
        esptool.write_flash(esp, [(0x1000, firmware_path)], flash_freq='keep', flash_mode='keep', flash_size='4MB')
        log("FINISHED FLASHING SUCCESSFULLY!")
        
        log("Resetting ESP32 into MicroPython runtime...")
        esp.hard_reset()
    except Exception as e:
        log(f"EXCEPTIONAL EXIT: {type(e).__name__}: {e}")
        with open(LOG_FILE, "a") as f:
            traceback.print_exc(file=f)

if __name__ == '__main__':
    main()
