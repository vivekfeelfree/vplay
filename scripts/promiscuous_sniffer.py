#!/usr/bin/env python3
"""Run the FHSS promiscuous preamble sniffer on the connected ESP32 (`vplay run promiscuous`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_PROMISCUOUS_SCRIPT = get_preset("promiscuous").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "promiscuous", *sys.argv[1:]]))
