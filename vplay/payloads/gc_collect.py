import gc

before = gc.mem_free()
gc.collect()
after = gc.mem_free()
print("Garbage Collection complete. Reclaimed:", after - before, "bytes.")
print("Current Free RAM Heap:", after, "bytes.")
