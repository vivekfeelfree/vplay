import machine


def probe_all_gpios():
    print("======================================================================")
    print("⚡ UNIVERSAL ESP32 GPIO PIN DISCOVERY & ELECTRICAL AUDIT")
    print("   Auditing 34 GPIO pins: Capabilities, Live State, ADC Voltages")
    print("======================================================================\n")
    all_gpios = [
        0, 2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35, 36, 39
    ]
    input_only = [34, 35, 36, 39]
    touch_pins = {4: 0, 0: 1, 2: 2, 15: 3, 13: 4, 12: 5, 14: 6, 27: 7, 33: 8, 32: 9}
    adc_pins = [32, 33, 34, 35, 36, 39, 4, 0, 2, 13, 12, 14, 27, 25, 26]
    for pin_num in all_gpios:
        caps = ["INPUT-ONLY" if pin_num in input_only else "IN/OUT"]
        if pin_num in adc_pins:
            caps.append("ADC")
        if pin_num in touch_pins:
            caps.append("TOUCH")
        if pin_num in [25, 26]:
            caps.append("DAC")
        try:
            p = machine.Pin(pin_num, machine.Pin.IN)
            val = p.value()
            state_str = "State: %d (%s)" % (val, "HIGH/3.3V" if val else "LOW/0V")
        except Exception:
            state_str = "State: N/A"
        if pin_num in [32, 33, 34, 35, 36, 39]:
            try:
                adc = machine.ADC(machine.Pin(pin_num))
                raw_adc = adc.read()
                volts = (raw_adc / 4095.0) * 3.3
                state_str += " | Voltage: %.2fV (raw %d)" % (volts, raw_adc)
            except Exception:
                pass
        print("GPIO %2d | %-26s | %s" % (pin_num, ", ".join(caps), state_str))
    print("\n======================================================================")


probe_all_gpios()
