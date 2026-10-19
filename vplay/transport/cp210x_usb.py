"""Raw CP210x backend over PyUSB/libusb - no OS serial driver required.

This is the path proven on Android/Termux (Pixel 8 Pro), where unrooted apps cannot
open ``/dev/ttyUSB*``: Termux grants the USB device via ``termux-usb`` and we speak
the Silicon Labs CP210x vendor protocol (AN571) ourselves.

It also works on desktop OSes if the CP2102 is bound to a libusb-compatible driver
(WinUSB via Zadig on Windows; on Linux the ``cp210x`` kernel module is detached).
"""

from __future__ import annotations

import os
import struct

from vplay import hostinfo
from vplay.config import CP210X_PID, CP210X_VID
from vplay.transport.base import DeviceBusyError, DeviceNotFoundError, Transport, TransportError

# CP210x vendor requests (Silicon Labs AN571).
REQTYPE_HOST_TO_INTERFACE = 0x41
CP210X_IFC_ENABLE = 0x00
CP210X_SET_LINE_CTL = 0x03
CP210X_SET_MHS = 0x07
CP210X_SET_BAUDRATE = 0x1E

UART_ENABLE = 0x0001
LINE_8N1 = 0x0800  # 8 data bits, no parity, 1 stop bit
MHS_MASK_DTR_RTS = 0x0300  # upper byte: which lines the request updates

EP_OUT = 0x01
EP_IN = 0x81
INTERFACE = 0


def _load_usb():
    try:
        import usb.core  # noqa: F401
        import usb.util  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on host
        raise TransportError(
            "The 'usb' backend needs PyUSB: pip install pyusb "
            "(Termux: pkg install libusb && pip install pyusb)"
        ) from exc
    import usb

    return usb


def get_libusb_backend():
    """Locate a libusb-1.0 backend for the current host."""
    _load_usb()
    import usb.backend.libusb1 as libusb1

    prefix = hostinfo.termux_prefix()
    if prefix:
        lib = os.path.join(prefix, "lib", "libusb-1.0.so")
        backend = libusb1.get_backend(find_library=lambda _name: lib)
        if backend is None:
            raise TransportError(f"Cannot load {lib}. Run: pkg install libusb")
        return backend

    backend = libusb1.get_backend()
    if backend is None:
        try:  # Optional helper that bundles libusb-1.0.dll for Windows.
            import libusb_package

            backend = libusb_package.get_libusb1_backend()
        except ImportError:
            pass
    if backend is None:
        raise TransportError(
            "libusb-1.0 not found. On Windows: pip install libusb-package; "
            "on Linux: install libusb-1.0-0; or use the 'serial' backend instead."
        )
    return backend


def _is_busy(exc: Exception) -> bool:
    return getattr(exc, "errno", None) in (13, 16) or any(
        s in str(exc) for s in ("Resource busy", "Access denied", "LIBUSB_ERROR_ACCESS", "LIBUSB_ERROR_BUSY")
    )


class Cp210xUsbTransport(Transport):
    backend = "usb"

    def __init__(self, baudrate: int = 115200, vid: int = CP210X_VID, pid: int = CP210X_PID) -> None:
        self._baudrate = baudrate
        self._vid, self._pid = vid, pid
        self._dev = None
        self._usb = None
        self._dtr = False
        self._rts = False

    @property
    def description(self) -> str:
        return f"USB {self._vid:04x}:{self._pid:04x} @ {self._baudrate} baud (raw CP210x/libusb)"

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    # -------------------------------------------------------------- lifecycle

    def open(self) -> None:
        if self.is_open:
            return
        usb = _load_usb()
        backend = get_libusb_backend()
        dev = usb.core.find(idVendor=self._vid, idProduct=self._pid, backend=backend)
        if dev is None:
            hint = (
                " On Termux start vplay through scripts/termux/vplay.sh so termux-usb "
                "grants USB access."
                if hostinfo.is_android()
                else ""
            )
            raise DeviceNotFoundError(f"No USB device {self._vid:04x}:{self._pid:04x} found.{hint}")
        try:
            try:
                if dev.is_kernel_driver_active(INTERFACE):
                    dev.detach_kernel_driver(INTERFACE)
            except (NotImplementedError, usb.core.USBError):
                pass  # Not supported on Windows/Android; harmless.
            try:
                dev.set_configuration()
            except usb.core.USBError as exc:
                if _is_busy(exc):
                    raise
            usb.util.claim_interface(dev, INTERFACE)
            self._dev, self._usb = dev, usb
            self._ctrl(CP210X_IFC_ENABLE, UART_ENABLE)
            self._ctrl(CP210X_SET_LINE_CTL, LINE_8N1)
            self._apply_baudrate()
            self.set_lines(dtr=False, rts=False)
        except usb.core.USBError as exc:
            self._release(dev, usb)
            self._dev = None
            if _is_busy(exc):
                raise DeviceBusyError(
                    "The CP2102 is claimed by another process (e.g. a running `vplay web`). "
                    "Stop it or use the web UI."
                ) from exc
            raise TransportError(f"USB setup failed: {exc}") from exc

    @staticmethod
    def _release(dev, usb) -> None:
        try:
            usb.util.release_interface(dev, INTERFACE)
        except Exception:
            pass
        try:
            usb.util.dispose_resources(dev)
        except Exception:
            pass

    def close(self) -> None:
        if self._dev is not None:
            self._release(self._dev, self._usb)
            self._dev = None

    # ---------------------------------------------------------------- control

    def _ctrl(self, request: int, value: int, data: bytes | None = None) -> None:
        self._dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, request, value, INTERFACE, data)

    def _apply_baudrate(self) -> None:
        self._ctrl(CP210X_SET_BAUDRATE, 0, struct.pack("<I", self._baudrate))

    def set_baudrate(self, baudrate: int) -> None:
        self._baudrate = baudrate
        if self.is_open:
            self._apply_baudrate()

    def set_lines(self, *, dtr: bool, rts: bool) -> None:
        self._dtr, self._rts = dtr, rts
        if self.is_open:
            value = MHS_MASK_DTR_RTS | (0x01 if dtr else 0) | (0x02 if rts else 0)
            self._ctrl(CP210X_SET_MHS, value)

    # -------------------------------------------------------------------- I/O

    def write(self, data: bytes) -> None:
        if not self.is_open:
            raise TransportError("Transport is not open")
        view = memoryview(data)
        try:
            while view:
                sent = self._dev.write(EP_OUT, view[:4096], timeout=2000)
                view = view[sent:]
        except self._usb.core.USBError as exc:
            raise TransportError(f"USB write failed: {exc}") from exc

    def read(self, max_bytes: int = 4096, timeout: float = 0.05) -> bytes:
        if not self.is_open:
            raise TransportError("Transport is not open")
        try:
            data = self._dev.read(EP_IN, max(64, max_bytes), timeout=max(1, int(timeout * 1000)))
            return bytes(data)
        except self._usb.core.USBTimeoutError:
            return b""
        except self._usb.core.USBError as exc:
            if getattr(exc, "errno", None) == 110 or "timed out" in str(exc).lower():
                return b""
            raise TransportError(f"USB read failed: {exc}") from exc
