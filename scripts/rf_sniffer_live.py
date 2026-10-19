#!/usr/bin/env python3
"""Run the live 2.4GHz gamepad packet sniffer on the connected ESP32 (`vplay run sniffer_live`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_SNIFFER_SCRIPT = get_preset("sniffer_live").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "sniffer_live", *sys.argv[1:]]))
