#!/usr/bin/env python3
"""Blink the onboard blue LED on the connected ESP32 (`vplay run blink`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_BLINK_SCRIPT = get_preset("blink").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "blink", *sys.argv[1:]]))
