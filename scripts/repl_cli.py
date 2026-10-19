#!/usr/bin/env python3
"""Open the interactive MicroPython REPL terminal (portable wrapper around ``vplay.terminal``)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["repl", *sys.argv[1:]]))
