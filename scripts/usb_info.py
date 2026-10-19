#!/usr/bin/env python3
"""Run platform, serial port, USB, and ESP32 link diagnostics (wrapper around ``vplay doctor``)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["doctor", *sys.argv[1:]]))
