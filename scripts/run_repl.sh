#!/usr/bin/env bash
# Launch interactive MicroPython REPL CLI (Android/Termux, Linux, macOS)

set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPL_SCRIPT="$REPO_ROOT/scripts/repl_cli.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if command -v termux-usb >/dev/null 2>&1; then
    DEV="$(termux-usb -l | jq -r '.[0]' 2>/dev/null)"
    if [ -z "$DEV" ] || [ "$DEV" = "null" ]; then
        echo "❌ No USB OTG device detected by termux-usb."
        echo "   Please make sure your ESP32 board is connected via USB OTG data cable."
        exit 1
    fi
    echo "FOUND USB DEVICE: $DEV"
    exec termux-usb -E -e "$REPL_SCRIPT" "$DEV"
else
    exec "$PYTHON_BIN" "$REPL_SCRIPT" "$@"
fi
