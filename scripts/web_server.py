#!/usr/bin/env python3
"""Launch the vplay Web Control Center (portable wrapper around ``vplay.web``)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["web", *sys.argv[1:]]))
