import machine
import time

PIN_LED = globals().get("PIN_LED", 2)

led = machine.Pin(PIN_LED, machine.Pin.OUT)
for _ in range(5):
    led.value(1)
    time.sleep(0.3)
    led.value(0)
    time.sleep(0.3)
print("SUCCESS: Onboard Blue LED (GPIO%d) blinked 5 times!" % PIN_LED)
