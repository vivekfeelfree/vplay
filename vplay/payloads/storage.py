import os

print("=== ESP32 FLASH FILE SYSTEM DIAGNOSTICS ===")
stat = os.statvfs("/")
total_bytes = stat[0] * stat[2]
free_bytes = stat[0] * stat[4]
print("Total Flash Storage :", total_bytes // 1024, "KB")
print("Free Flash Storage  :", free_bytes // 1024, "KB")
print("Root Files Listing  :", os.listdir("/"))
