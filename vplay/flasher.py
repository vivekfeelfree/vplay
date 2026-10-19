"""Cross-platform ESP32 firmware flasher built on top of :class:`~vplay.transport.Transport`.

Works identically over:
* ``SerialTransport`` (Windows COMx, Linux /dev/ttyUSBx, macOS /dev/cu.*)
* ``Cp210xUsbTransport`` (Android/Termux raw USB over PyUSB/libusb)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from vplay.config import DeviceConfig
from vplay.transport import Transport, open_transport

DEFAULT_FIRMWARE = Path(__file__).resolve().parent.parent / "ESP32_GENERIC-v1.22.2.bin"


class TransportSerialAdapter:
    """Adapts any :class:`~vplay.transport.Transport` to the pyserial interface expected by ``esptool``."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport
        self._buf = bytearray()
        self._baudrate = 115200
        self._dtr = False
        self._rts = False
        self.timeout: float | None = 0.5
        self.write_timeout: float | None = 10.0
        self.port = transport.description
        self.name = transport.description

    @property
    def is_open(self) -> bool:
        return self._t.is_open

    def isOpen(self) -> bool:  # noqa: N802 (legacy pyserial API)
        return self._t.is_open

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int) -> None:
        self._baudrate = int(value)
        self._t.set_baudrate(self._baudrate)

    def setDTR(self, level: bool) -> None:  # noqa: N802
        self._dtr = bool(level)
        self._t.set_lines(dtr=self._dtr, rts=self._rts)

    def setRTS(self, level: bool) -> None:  # noqa: N802
        self._rts = bool(level)
        self._t.set_lines(dtr=self._dtr, rts=self._rts)

    @property
    def dtr(self) -> bool:
        return self._dtr

    @dtr.setter
    def dtr(self, value: bool) -> None:
        self.setDTR(value)

    @property
    def rts(self) -> bool:
        return self._rts

    @rts.setter
    def rts(self, value: bool) -> None:
        self.setRTS(value)

    @property
    def in_waiting(self) -> int:
        return len(self._buf)

    def inWaiting(self) -> int:  # noqa: N802
        return len(self._buf)

    @property
    def out_waiting(self) -> int:
        return 0

    def outWaiting(self) -> int:  # noqa: N802
        return 0

    def write(self, data: bytes | bytearray) -> int:
        payload = bytes(data)
        if not payload:
            return 0
        self._t.write(payload)
        return len(payload)

    def read(self, size: int = 1) -> bytes:
        if self.timeout is not None and self.timeout >= 10.0:
            wait = max(self.timeout, 120.0)
        else:
            wait = self.timeout if (self.timeout is not None and self.timeout > 0) else 0.2
        deadline = time.monotonic() + wait
        while len(self._buf) < size and time.monotonic() < deadline:
            chunk = self._t.read(max(64, size - len(self._buf)), timeout=0.02)
            if chunk:
                self._buf.extend(chunk)
        out = bytes(self._buf[:size])
        del self._buf[:size]
        return out

    def flush(self) -> None:
        pass

    def reset_input_buffer(self) -> None:
        self._buf.clear()
        self._t.drain(quiet_time=0.02, max_time=0.2)

    def reset_output_buffer(self) -> None:
        pass

    def flushInput(self) -> None:  # noqa: N802
        self.reset_input_buffer()

    def flushOutput(self) -> None:  # noqa: N802
        self.reset_output_buffer()

    def close(self) -> None:
        self._t.close()


def enter_bootloader(adapter: TransportSerialAdapter) -> None:
    """Classic ESP32 DevKit auto-reset sequence into ROM serial bootloader."""
    adapter.setDTR(False)
    adapter.setRTS(True)
    time.sleep(0.1)
    adapter.setDTR(True)
    adapter.setRTS(False)
    time.sleep(0.05)
    adapter.setDTR(False)
    time.sleep(0.2)
    adapter.reset_input_buffer()


def flash_micropython(
    device_cfg: DeviceConfig,
    firmware_path: str | os.PathLike | None = None,
    *,
    address: int = 0x1000,
    baudrate: int = 460800,
    erase: bool = False,
) -> dict[str, str]:
    """Flash MicroPython firmware onto the connected ESP32.

    Returns a summary dictionary with chip model, MAC address, flash ID, and firmware path.
    """
    import esptool

    fw = Path(firmware_path) if firmware_path else DEFAULT_FIRMWARE
    if not fw.is_file():
        raise FileNotFoundError(f"Firmware image not found: {fw}")

    print("=== vplay Cross-Platform ESP32 Firmware Flasher ===", flush=True)
    print(f"Firmware File : {fw} ({fw.stat().st_size:,} bytes)", flush=True)

    with open_transport(device_cfg) as transport:
        print(f"Active Link   : {transport.description}", flush=True)
        adapter = TransportSerialAdapter(transport)
        enter_bootloader(adapter)

        print("\n[Step 1/4] Connecting to ESP32 ROM bootloader...", flush=True)
        esp = esptool.detect_chip(adapter)
        chip_name = esp.CHIP_NAME
        features = ", ".join(esp.get_chip_features())
        print(f"  Chip Model  : {chip_name} ({features})", flush=True)

        print("\n[Step 2/4] Uploading RAM stub flasher...", flush=True)
        esp = esp.run_stub()
        mac_str = ":".join(f"{b:02x}" for b in esp.read_mac())
        flash_id = esp.flash_id()
        print(f"  MAC Address : {mac_str}", flush=True)
        print(f"  Flash ID    : 0x{flash_id:06x}", flush=True)

        if baudrate and baudrate != 115200:
            try:
                esp.change_baud(baudrate)
                print(f"  Baud Rate   : {baudrate}", flush=True)
            except Exception as exc:
                print(f"  Baud Rate   : keeping 115200 ({exc})", flush=True)

        if erase:
            print("\n[Step 3/4] Erasing SPI Flash...", flush=True)
            esptool.erase_flash(esp)
        else:
            print("\n[Step 3/4] Skipping full chip erase (pass --erase to force)...", flush=True)

        print(f"\n[Step 4/4] Writing firmware at 0x{address:04x}...", flush=True)
        esptool.write_flash(
            esp,
            [(address, str(fw))],
            flash_freq="keep",
            flash_mode="keep",
            flash_size="4MB",
        )
        print("\nResetting ESP32 into MicroPython runtime...", flush=True)
        esp.hard_reset()
        print("=== SUCCESS: MicroPython Firmware Deployed! ===", flush=True)
        return {
            "chip": chip_name,
            "mac": mac_str,
            "flash_id": f"0x{flash_id:06x}",
            "firmware": str(fw),
        }
