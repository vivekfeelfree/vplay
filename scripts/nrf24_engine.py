#!/usr/bin/env python3
"""Deploy and run the NRF24Controller register-level driver & diagnostics (`vplay run nrf24_driver`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vplay.cli import main  # noqa: E402
from vplay.payloads import get_preset  # noqa: E402

MICROPYTHON_NRF24_DRIVER = get_preset("nrf24_driver").render()

if __name__ == "__main__":
    raise SystemExit(main(["run", "nrf24_driver", *sys.argv[1:]]))
