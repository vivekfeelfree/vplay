#!/usr/bin/env python3
"""Run the 9-way multi-address & rate framing exercise (`vplay run live_exercise`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

LIVE_EXERCISE_MICROPYTHON = get_preset("live_exercise").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "live_exercise", *sys.argv[1:]]))
