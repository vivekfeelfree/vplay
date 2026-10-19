#!/usr/bin/env python3
"""Auto-discover nRF24L01+/Si24R1 SPI pins on the connected ESP32 (`vplay run auto_discover`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_AUTO_DISCOVER_SCRIPT = get_preset("auto_discover").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "auto_discover", *sys.argv[1:]]))
