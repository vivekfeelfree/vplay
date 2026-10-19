#!/usr/bin/env python3
"""Audit all 34 ESP32 GPIO pins & ADC voltages (`vplay run probe_gpios`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_PROBE_SCRIPT = get_preset("probe_gpios").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "probe_gpios", *sys.argv[1:]]))
