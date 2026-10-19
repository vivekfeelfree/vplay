"""Configuration: the single source of truth for pins, device link and web settings.

Precedence (lowest to highest):
    built-in defaults  <  vplay.toml  <  VPLAY_* environment variables  <  CLI flags

Config file lookup: ``--config PATH``, else ``$VPLAY_CONFIG``, else ``./vplay.toml``.
See ``vplay.example.toml`` in the repository root for every key.
"""

from __future__ import annotations

import dataclasses
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# USB identity of the Silicon Labs CP2102 bridge on the ESP32 DevKit v1.
CP210X_VID = 0x10C4
CP210X_PID = 0xEA60


@dataclass(frozen=True)
class Pins:
    """ESP32 GPIO wiring of the nRF24L01+/Si24R1 module.

    Default is the HSPI mapping verified on hardware (see README / JOURNAL).
    """

    sck: int = 14
    mosi: int = 13
    miso: int = 12
    csn: int = 15
    ce: int = 16
    spi_id: int = 1  # MicroPython machine.SPI id (1 = HSPI, 2 = VSPI on ESP32)
    spi_baudrate: int = 4_000_000
    led: int = 2

    def as_dict(self) -> dict[str, int]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class DeviceConfig:
    """How to reach the board.

    backend: ``auto`` | ``serial`` | ``usb``
        auto   -> ``usb`` on Android/Termux, ``serial`` everywhere else
        serial -> pyserial on a COM/tty port (needs the OS CP210x driver)
        usb    -> raw CP210x protocol over PyUSB/libusb (no OS driver needed)
    port: explicit COM/tty port (serial backend). Empty = auto-detect by VID:PID.
    """

    backend: str = "auto"
    port: str = ""
    baudrate: int = 115200
    vid: int = CP210X_VID
    pid: int = CP210X_PID


@dataclass(frozen=True)
class WebConfig:
    # Loopback by default: /api/exec runs arbitrary code on the board.
    host: str = "127.0.0.1"
    port: int = 8080


@dataclass(frozen=True)
class Config:
    pins: Pins = field(default_factory=Pins)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    web: WebConfig = field(default_factory=WebConfig)
    source: str = "defaults"

    def replace(self, **sections: dict[str, Any]) -> "Config":
        """Return a copy with selected section fields overridden (``None`` values ignored)."""
        updated = {}
        for name, overrides in sections.items():
            clean = {k: v for k, v in overrides.items() if v is not None}
            updated[name] = dataclasses.replace(getattr(self, name), **clean)
        return dataclasses.replace(self, **updated)


_SECTIONS = {"pins": Pins, "device": DeviceConfig, "web": WebConfig}


def _coerce(cls: type, key: str, value: Any) -> Any:
    target = {f.name: f.type for f in dataclasses.fields(cls)}[key]
    if target in ("int", int):
        return int(value, 0) if isinstance(value, str) else int(value)
    return str(value)


def _section_from_mapping(cls: type, data: dict[str, Any], origin: str) -> dict[str, Any]:
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"{origin}: unknown key(s) {sorted(unknown)}; allowed: {sorted(known)}")
    return {k: _coerce(cls, k, v) for k, v in data.items()}


def _env_overrides() -> dict[str, dict[str, Any]]:
    """Read ``VPLAY_<SECTION>_<KEY>`` variables, e.g. ``VPLAY_DEVICE_PORT=COM5``."""
    result: dict[str, dict[str, Any]] = {}
    for section, cls in _SECTIONS.items():
        for f in dataclasses.fields(cls):
            raw = os.environ.get(f"VPLAY_{section}_{f.name}".upper())
            if raw is not None and raw != "":
                result.setdefault(section, {})[f.name] = _coerce(cls, f.name, raw)
    return result


def find_config_file(explicit: str | os.PathLike | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
        return path
    env = os.environ.get("VPLAY_CONFIG")
    if env:
        return find_config_file(env)
    local = Path.cwd() / "vplay.toml"
    return local if local.is_file() else None


def load_config(path: str | os.PathLike | None = None) -> Config:
    cfg = Config()
    file = find_config_file(path)
    if file is not None:
        with open(file, "rb") as fh:
            data = tomllib.load(fh)
        unknown = set(data) - set(_SECTIONS)
        if unknown:
            raise ValueError(f"{file}: unknown section(s) {sorted(unknown)}")
        cfg = cfg.replace(
            **{s: _section_from_mapping(_SECTIONS[s], data[s], f"{file} [{s}]") for s in data}
        )
        cfg = dataclasses.replace(cfg, source=str(file))
    env = _env_overrides()
    if env:
        cfg = cfg.replace(**env)
        cfg = dataclasses.replace(cfg, source=f"{cfg.source} + env")
    return cfg
