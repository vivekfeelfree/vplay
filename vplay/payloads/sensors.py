import esp32
import machine

print("=== ESP32 INTERNAL HARDWARE SENSORS & TELEMETRY ===")
try:
    temp_f = esp32.raw_temperature()
    temp_c = (temp_f - 32) * 5.0 / 9.0
    print("Internal SoC Junction Temp :", temp_f, "°F (%.1f °C)" % temp_c)
except Exception as e:
    print("Temp Sensor Error:", e)

try:
    adc = machine.ADC(machine.Pin(34))
    print("Analog ADC Input (GPIO34)  :", adc.read(), "raw (0-4095)")
except Exception as e:
    print("ADC Reading Error:", e)
