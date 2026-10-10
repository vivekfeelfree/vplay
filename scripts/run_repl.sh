#!/data/data/com.termux/files/usr/bin/bash
# Helper script to dynamically query USB device node and run MicroPython REPL CLI

DEV=$(termux-usb -l | jq -r '.[0]' 2>/dev/null)

if [ -z "$DEV" ] || [ "$DEV" == "null" ]; then
    echo "❌ No USB OTG device detected by termux-usb."
    echo "   Please make sure your ESP32 board is connected via USB OTG data cable."
    exit 1
fi

echo "FOUND USB DEVICE: $DEV"
echo "Starting MicroPython REPL CLI..."
termux-usb -E -e /data/data/com.termux/files/home/trials/vplay/scripts/repl_cli.py "$DEV"
