#!/data/data/com.termux/files/usr/bin/python3
import os
import sys

print("=== TERMUX USB TEST ===")
print("TERMUX_USB_FD:", os.environ.get("TERMUX_USB_FD"))
print("sys.argv:", sys.argv)
