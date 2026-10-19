"""Device-side MicroPython payloads and preset registry.

Every preset lives as a real, standalone `.py` file in this directory (syntax-checked,
editable, and copyable directly onto an ESP32), and is rendered with the active
:class:`~vplay.config.Pins` configuration before being sent over the Raw REPL.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vplay.config import Pins

_PAYLOAD_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Preset:
    key: str
    title: str
    desc: str
    filename: str
    timeout: float = 15.0

    @property
    def path(self) -> Path:
        return _PAYLOAD_DIR / self.filename

    def raw_source(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def render(self, pins: Pins | None = None) -> str:
        pins = pins or Pins()
        header = (
            f"# Configured hardware pin map (vplay)\n"
            f"PIN_SCK = {pins.sck}; PIN_MOSI = {pins.mosi}; PIN_MISO = {pins.miso}; "
            f"PIN_CSN = {pins.csn}; PIN_CE = {pins.ce}; "
            f"SPI_ID = {pins.spi_id}; SPI_BAUDRATE = {pins.spi_baudrate}; PIN_LED = {pins.led}\n\n"
        )
        return header + self.raw_source()


PRESET_LIST: tuple[Preset, ...] = (
    Preset(
        key="blink",
        title="🔵 Blink Blue LED (GPIO2)",
        desc="Pulses the onboard blue LED 5 times at 300ms intervals.",
        filename="blink.py",
        timeout=10.0,
    ),
    Preset(
        key="specs",
        title="🧠 Full SoC & System Diagnostics",
        desc="Retrieves CPU frequency, RAM heap allocations, VFS storage stats, and unique chip ID.",
        filename="specs.py",
        timeout=8.0,
    ),
    Preset(
        key="sensors",
        title="🌡️ Internal Thermal & ADC Telemetry",
        desc="Reads the built-in raw temperature sensor (°F and °C) and analog ADC voltage telemetry.",
        filename="sensors.py",
        timeout=8.0,
    ),
    Preset(
        key="probe_gpios",
        title="⚡ Universal GPIO Pin Inspector & Electrical Prober",
        desc="Audits all 34 GPIO pins on the ESP32: discovers capabilities (IN/OUT, ADC, Touch, DAC) and reads live voltages & logic states.",
        filename="probe_gpios.py",
        timeout=10.0,
    ),
    Preset(
        key="storage",
        title="💾 Flash Storage & File System",
        desc="Inspects Flash VFS partition size, used block statistics, and root directory file list.",
        filename="storage.py",
        timeout=8.0,
    ),
    Preset(
        key="clock_240",
        title="⚡ Set CPU Frequency to 240 MHz",
        desc="Scales ESP32 dual-core clock to maximum performance (240 MHz).",
        filename="clock_240.py",
        timeout=8.0,
    ),
    Preset(
        key="clock_160",
        title="🌿 Set CPU Frequency to 160 MHz",
        desc="Scales ESP32 clock to balanced efficiency mode (160 MHz).",
        filename="clock_160.py",
        timeout=8.0,
    ),
    Preset(
        key="spi_scan",
        title="📡 NRF24 SPI Register Matrix Dump",
        desc="Queries all transceiver registers across the configured HSPI (D14/D13/D12/D15/D16) and VSPI pin maps.",
        filename="spi_scan.py",
        timeout=10.0,
    ),
    Preset(
        key="auto_discover",
        title="🔍 Auto-Discover NRF24 SPI Pins",
        desc="Dynamically scans GPIO pin combinations (HSPI, VSPI, Alt pinsets) to auto-detect where the NRF24 card is wired.",
        filename="auto_discover.py",
        timeout=12.0,
    ),
    Preset(
        key="rf_sweep",
        title="📶 2.4GHz RF Spectrum Carrier Sweeper & Promiscuous Sniffer",
        desc="Scans channels 0-80 (2.400-2.480 GHz) while you press buttons, auto-locks onto the active channel, & promiscuously intercepts raw packets.",
        filename="rf_sweep.py",
        timeout=15.0,
    ),
    Preset(
        key="sniffer",
        title="🕵️ 2.4GHz Promiscuous Sniffer Setup Mode",
        desc="Configures Pipe 0 for un-addressed promiscuous listening on Channel 2 (2402 MHz).",
        filename="sniffer.py",
        timeout=8.0,
    ),
    Preset(
        key="sniffer_live",
        title="🎮 Live 2.4GHz Gamepad Packet Sniffer & Logger",
        desc="Listens for 3.0 seconds on Channel 58 (2458 MHz), capturing raw 32-byte wireless controller frames & printing hex bitmasks live.",
        filename="sniffer_live.py",
        timeout=12.0,
    ),
    Preset(
        key="promiscuous",
        title="🕵️ Universal Promiscuous Preamble Sniffer (FHSS Hopping)",
        desc="Disables CRC, sets 3-byte 0x55 0x55 0x55 preamble matching, & hops across channels [10, 25, 38, 48, 58, 64, 76] to intercept FHSS controllers.",
        filename="promiscuous.py",
        timeout=15.0,
    ),
    Preset(
        key="isolator",
        title="🔬 Gamepad Differential Signal Isolator",
        desc="Runs a 2-phase test comparing ambient Wi-Fi/BT baseline noise against active button press bursts to pinpoint the exact gamepad channel & payload.",
        filename="isolator.py",
        timeout=18.0,
    ),
    Preset(
        key="button_mapper",
        title="🎯 Live Controller Button Bitmask Mapper",
        desc="Captures promiscuous frames on Channel 58 and prints byte/bit diffs whenever a button state changes.",
        filename="button_mapper.py",
        timeout=15.0,
    ),
    Preset(
        key="live_exercise",
        title="🏆 9-Way Multi-Address & Rate Framing Exercise",
        desc="8-second spectrum carrier scan followed by a 9-configuration preamble/rate matrix scan across the top active channels.",
        filename="live_exercise.py",
        timeout=35.0,
    ),
    Preset(
        key="nrf24_driver",
        title="🧰 NRF24Controller Driver & Full Diagnostics Dump",
        desc="Loads the full register-level NRF24Controller class and dumps all register, carrier, FIFO, and pipe states.",
        filename="nrf24_driver.py",
        timeout=10.0,
    ),
    Preset(
        key="gc",
        title="🧹 Memory Garbage Collector & Trim",
        desc="Forces MicroPython garbage collection and reports reclaimed memory heap space.",
        filename="gc_collect.py",
        timeout=8.0,
    ),
)

PRESETS: dict[str, Preset] = {p.key: p for p in PRESET_LIST}


def get_preset(key: str) -> Preset:
    if key not in PRESETS:
        available = ", ".join(PRESETS)
        raise KeyError(f"Unknown preset {key!r}. Available presets: {available}")
    return PRESETS[key]


def serialize_presets(pins: Pins | None = None) -> dict[str, dict[str, str]]:
    """Format presets dictionary for the Web Control Center frontend."""
    pins = pins or Pins()
    return {
        p.key: {
            "title": p.title,
            "desc": p.desc,
            "script": p.render(pins),
        }
        for p in PRESET_LIST
    }
