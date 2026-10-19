#!/usr/bin/env python3
"""Scan nRF24L01+/Si24R1 SPI registers on the connected ESP32 (`vplay run spi_scan`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_SPI_SCAN_SCRIPT = get_preset("spi_scan").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "spi_scan", *sys.argv[1:]]))
