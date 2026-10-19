#!/usr/bin/env python3
"""Flash MicroPython with full console & log file output (portable wrapper around ``vplay.flasher``)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["flash", *sys.argv[1:]]))
