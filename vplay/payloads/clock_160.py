import machine

machine.freq(160000000)
print("CPU Frequency updated to:", machine.freq() // 1000000, "MHz [BALANCED]")
