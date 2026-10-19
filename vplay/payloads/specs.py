import gc
import machine
import os
import sys
import ubinascii

print("=== ESP32 FULL SYSTEM SPECS & DIAGNOSTICS ===")
print("Platform         :", sys.platform)
print("MicroPython Build:", sys.version)
print("CPU Frequency    :", machine.freq() // 1000000, "MHz")
print("Chip Unique ID   :", ubinascii.hexlify(machine.unique_id()).decode())
print("Reset Reason Code:", machine.reset_cause())
print("Free RAM Heap    :", gc.mem_free(), "bytes")
print("Allocated RAM    :", gc.mem_alloc(), "bytes")
print("Storage VFS Stat :", os.statvfs("/"))
