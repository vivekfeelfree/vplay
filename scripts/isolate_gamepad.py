#!/usr/bin/env python3
"""Run the 2-phase differential gamepad noise isolator (`vplay run isolator`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_ISOLATOR_SCRIPT = get_preset("isolator").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "isolator", *sys.argv[1:]]))
