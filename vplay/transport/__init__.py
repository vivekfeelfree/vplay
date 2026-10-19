"""Transport selection.

``open_transport(cfg)`` is the only place that decides *how* to reach the board:

=========  =====================================================================
backend    behaviour
=========  =====================================================================
auto       Android/Termux -> ``usb``; Windows/Linux/macOS -> ``serial``
serial     pyserial on an OS COM/tty port (auto-detected by VID:PID or ``port``)
usb        raw CP210x over PyUSB/libusb
=========  =====================================================================
"""

from __future__ import annotations

from vplay import hostinfo
from vplay.config import DeviceConfig
from vplay.transport.base import DeviceBusyError, DeviceNotFoundError, Transport, TransportError

__all__ = [
    "Transport",
    "TransportError",
    "DeviceNotFoundError",
    "DeviceBusyError",
    "BACKENDS",
    "resolve_backend",
    "create_transport",
    "open_transport",
]

BACKENDS = ("auto", "serial", "usb")


def resolve_backend(requested: str) -> str:
    requested = (requested or "auto").lower()
    if requested not in BACKENDS:
        raise ValueError(f"Unknown backend {requested!r}; choose from {BACKENDS}")
    if requested != "auto":
        return requested
    return "usb" if hostinfo.is_android() else "serial"


def create_transport(cfg: DeviceConfig) -> Transport:
    """Build (but do not open) the transport described by ``cfg``."""
    backend = resolve_backend(cfg.backend)
    if backend == "serial":
        from vplay.transport.serial_port import SerialTransport

        return SerialTransport(port=cfg.port or None, baudrate=cfg.baudrate, vid=cfg.vid, pid=cfg.pid)
    from vplay.transport.cp210x_usb import Cp210xUsbTransport

    return Cp210xUsbTransport(baudrate=cfg.baudrate, vid=cfg.vid, pid=cfg.pid)


def open_transport(cfg: DeviceConfig) -> Transport:
    transport = create_transport(cfg)
    transport.open()
    return transport
