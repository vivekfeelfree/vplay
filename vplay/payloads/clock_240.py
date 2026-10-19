import machine

machine.freq(240000000)
print("CPU Frequency updated to:", machine.freq() // 1000000, "MHz [MAX PERFORMANCE]")
