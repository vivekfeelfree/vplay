"""Transport interface: a raw, bidirectional byte link to the ESP32's USB-UART bridge.

Higher layers (Raw REPL, flasher, terminal) only ever talk to :class:`Transport`,
so they are identical on every OS. Each concrete backend hides one OS-specific way
of reaching the CP2102:

* :class:`vplay.transport.serial_port.SerialTransport` - OS driver + pyserial
  (Windows COMx, Linux /dev/ttyUSBx, macOS /dev/cu.*)
* :class:`vplay.transport.cp210x_usb.Cp210xUsbTransport` - raw CP210x vendor
  protocol over PyUSB/libusb (Android/Termux, or WinUSB/libusb setups)
"""

from __future__ import annotations

import abc
import time


class TransportError(Exception):
    """Base class for link-level failures."""


class DeviceNotFoundError(TransportError):
    """No matching board is attached (or the OS driver is missing)."""


class DeviceBusyError(TransportError):
    """The board exists but another process holds it open."""


class Transport(abc.ABC):
    """Abstract byte link. Implementations must be usable as context managers."""

    #: Short backend id, e.g. ``"serial"`` or ``"usb"``.
    backend: str = "?"

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Human-readable identity, e.g. ``"COM5 (CP2102 USB to UART Bridge)"``."""

    @property
    @abc.abstractmethod
    def is_open(self) -> bool: ...

    @abc.abstractmethod
    def open(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @abc.abstractmethod
    def write(self, data: bytes) -> None:
        """Write all of ``data`` or raise :class:`TransportError`."""

    @abc.abstractmethod
    def read(self, max_bytes: int = 4096, timeout: float = 0.05) -> bytes:
        """Return up to ``max_bytes`` bytes; waits at most ``timeout`` seconds for the
        first byte and returns ``b""`` if none arrived."""

    @abc.abstractmethod
    def set_lines(self, *, dtr: bool, rts: bool) -> None:
        """Drive the DTR/RTS modem lines (wired to GPIO0/EN on ESP32 DevKits)."""

    @abc.abstractmethod
    def set_baudrate(self, baudrate: int) -> None: ...

    # ----------------------------------------------------------------- helpers

    def drain(self, quiet_time: float = 0.05, max_time: float = 1.0) -> bytes:
        """Discard incoming bytes until the line has been quiet for ``quiet_time``."""
        collected = bytearray()
        deadline = time.monotonic() + max_time
        while time.monotonic() < deadline:
            chunk = self.read(4096, timeout=quiet_time)
            if not chunk:
                break
            collected += chunk
        return bytes(collected)

    def __enter__(self) -> "Transport":
        if not self.is_open:
            self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.description}>"
