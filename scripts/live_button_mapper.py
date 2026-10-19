#!/usr/bin/env python3
"""Run the live controller button bitmask mapper (`vplay run button_mapper`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_BUTTON_MAPPER = get_preset("button_mapper").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "button_mapper", *sys.argv[1:]]))
