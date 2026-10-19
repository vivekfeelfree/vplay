"""pyserial backend: Windows COMx, Linux /dev/ttyUSBx, macOS /dev/cu.* ports.

Requires the OS USB-UART driver (on Windows: Silicon Labs "CP210x Universal Windows
Driver"). The board is found automatically by its USB VID:PID.
"""

from __future__ import annotations

import errno
from dataclasses import dataclass
from pathlib import Path

import serial
from serial.tools import list_ports

from vplay import hostinfo
from vplay.config import CP210X_PID, CP210X_VID
from vplay.transport.base import DeviceBusyError, DeviceNotFoundError, Transport, TransportError

_BUNDLED_INF = (
    Path(__file__).resolve().parent.parent.parent
    / "datasheets"
    / "cp210x_windows_driver"
    / "silabser.inf"
)

WINDOWS_DRIVER_HINT = (
    "On Windows the CP2102 needs the Silicon Labs VCP driver.\n"
    f"  Run once in an Administrator PowerShell/Command Prompt:\n"
    f'    pnputil /add-driver "{_BUNDLED_INF}" /install\n'
    "  (or open Explorer, right-click that silabser.inf file, and click 'Install')."
)


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str
    vid: int | None
    pid: int | None
    serial_number: str | None

    @property
    def is_cp210x(self) -> bool:
        return self.vid == CP210X_VID and self.pid == CP210X_PID


@dataclass(frozen=True)
class WindowsUsbPresence:
    instance_id: str
    description: str
    present: bool
    problem_code: int  # 0 = OK, 28 = CM_PROB_FAILED_INSTALL (no driver installed)


def probe_windows_pnp(vid: int = CP210X_VID, pid: int = CP210X_PID) -> WindowsUsbPresence | None:
    """Query Windows ConfigMgr (<1 ms, no admin needed) to see if the USB device is plugged in."""
    if not hostinfo.is_windows():
        return None
    try:
        import ctypes
        import winreg

        key_path = f"SYSTEM\\CurrentControlSet\\Enum\\USB\\VID_{vid:04X}&PID_{pid:04X}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            sub = winreg.EnumKey(key, 0)
            with winreg.OpenKey(key, sub) as subkey:
                try:
                    raw_desc, _ = winreg.QueryValueEx(subkey, "DeviceDesc")
                    desc = str(raw_desc).split(";")[-1]
                except OSError:
                    desc = "CP210x USB Device"
        instance_id = f"USB\\VID_{vid:04X}&PID_{pid:04X}\\{sub}"
        cfg = ctypes.windll.cfgmgr32
        devinst = ctypes.c_uint32()
        # CM_LOCATE_DEVNODE_NORMAL (0) succeeds only if the device is currently attached.
        if cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), instance_id, 0) != 0:
            return WindowsUsbPresence(instance_id, desc, present=False, problem_code=0)
        status = ctypes.c_uint32()
        problem = ctypes.c_uint32()
        cfg.CM_Get_DevNode_Status(ctypes.byref(status), ctypes.byref(problem), devinst, 0)
        return WindowsUsbPresence(instance_id, desc, present=True, problem_code=int(problem.value))
    except Exception:
        return None


def list_serial_ports() -> list[PortInfo]:
    return [
        PortInfo(p.device, p.description or "", p.vid, p.pid, p.serial_number)
        for p in sorted(list_ports.comports(), key=lambda p: p.device)
    ]


def find_port(vid: int = CP210X_VID, pid: int = CP210X_PID) -> str:
    """Return the device name of the single attached board matching ``vid:pid``."""
    matches = [p for p in list_serial_ports() if p.vid == vid and p.pid == pid]
    if not matches:
        pnp = probe_windows_pnp(vid, pid)
        if pnp and pnp.present and pnp.problem_code == 28:
            raise DeviceNotFoundError(
                f"USB device {vid:04x}:{pid:04x} ({pnp.description}) IS physically plugged in "
                f"({pnp.instance_id}),\nbut Windows has no driver installed for it "
                f"(Device Manager Error Code 28).\n{WINDOWS_DRIVER_HINT}"
            )
        hint = f"\n{WINDOWS_DRIVER_HINT}" if hostinfo.is_windows() else ""
        raise DeviceNotFoundError(
            f"No serial port with USB id {vid:04x}:{pid:04x} found. Is the board plugged in "
            f"with a data-capable cable?{hint}"
        )
    if len(matches) > 1:
        names = ", ".join(p.device for p in matches)
        raise DeviceNotFoundError(
            f"Several matching boards found ({names}); choose one with --port or [device] port."
        )
    return matches[0].device


def _is_busy_error(exc: Exception) -> bool:
    text = str(exc)
    return (
        "Access is denied" in text
        or "PermissionError" in text
        or "Resource busy" in text
        or "Could not exclusively lock" in text
        or getattr(exc, "errno", None) in (errno.EBUSY, errno.EACCES)
    )


class SerialTransport(Transport):
    backend = "serial"

    def __init__(
        self,
        port: str | None = None,
        baudrate: int = 115200,
        vid: int = CP210X_VID,
        pid: int = CP210X_PID,
    ) -> None:
        self._requested_port = port or None
        self._baudrate = baudrate
        self._vid, self._pid = vid, pid
        self._serial: serial.Serial | None = None
        self._port_name: str | None = port or None

    @property
    def port_name(self) -> str | None:
        return self._port_name

    @property
    def description(self) -> str:
        return f"{self._port_name or '<auto>'} @ {self._baudrate} baud (pyserial)"

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def open(self) -> None:
        if self.is_open:
            return
        self._port_name = self._requested_port or find_port(self._vid, self._pid)
        ser = serial.Serial()
        ser.port = self._port_name
        ser.baudrate = self._baudrate
        ser.timeout = 0
        ser.write_timeout = 2
        ser.dtr = False
        ser.rts = False
        if not hostinfo.is_windows():
            ser.exclusive = True
        try:
            ser.open()
        except serial.SerialException as exc:
            if _is_busy_error(exc):
                raise DeviceBusyError(
                    f"{self._port_name} is in use by another program (another vplay "
                    f"instance, Arduino IDE, Thonny, a serial monitor...). Close it and retry."
                ) from exc
            raise TransportError(f"Cannot open {self._port_name}: {exc}") from exc
        self._serial = ser

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def _require(self) -> serial.Serial:
        if not self.is_open:
            raise TransportError("Transport is not open")
        return self._serial  # type: ignore[return-value]

    def write(self, data: bytes) -> None:
        ser = self._require()
        try:
            ser.write(data)
            ser.flush()
        except serial.SerialException as exc:
            raise TransportError(f"Write to {self._port_name} failed: {exc}") from exc

    def read(self, max_bytes: int = 4096, timeout: float = 0.05) -> bytes:
        ser = self._require()
        try:
            ser.timeout = timeout
            first = ser.read(1)
            if not first:
                return b""
            waiting = ser.in_waiting
            rest = ser.read(min(waiting, max_bytes - 1)) if waiting and max_bytes > 1 else b""
            return first + rest
        except serial.SerialException as exc:
            raise TransportError(f"Read from {self._port_name} failed: {exc}") from exc

    def set_lines(self, *, dtr: bool, rts: bool) -> None:
        ser = self._require()
        ser.dtr = dtr
        ser.rts = rts

    def set_baudrate(self, baudrate: int) -> None:
        self._baudrate = baudrate
        if self.is_open:
            self._serial.baudrate = baudrate  # type: ignore[union-attr]
