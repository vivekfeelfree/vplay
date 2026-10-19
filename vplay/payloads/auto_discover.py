import machine


def auto_discover_nrf24():
    print("==================================================")
    print("🔍 AUTOMATED NRF24 SPI PIN DISCOVERY ENGINE")
    print("   Scanning GPIO pins for NRF24/Si24R1 response...")
    print("==================================================\n")
    fast_combinations = [
        ("HSPI Alt RX2 (CE=RX2/GPIO16)", 14, 13, 12, 15, 16),
        ("HSPI Standard (CE=D4)", 14, 13, 12, 15, 4),
        ("VSPI Standard (CE=D4)", 18, 23, 19, 5, 4),
        ("VSPI Alt RX2 (CE=RX2/GPIO16)", 18, 23, 19, 5, 16),
        ("HSPI Alt CSN 5", 14, 13, 12, 5, 4),
        ("VSPI Alt CSN 15", 18, 23, 19, 15, 4),
        ("Header Group 2", 25, 26, 27, 32, 33),
        ("Header Group 3", 27, 14, 12, 13, 15),
    ]
    found = False
    for name, sck_p, mosi_p, miso_p, csn_p, ce_p in fast_combinations:
        try:
            sck = machine.Pin(sck_p, machine.Pin.OUT)
            mosi = machine.Pin(mosi_p, machine.Pin.OUT)
            miso = machine.Pin(miso_p, machine.Pin.IN)
            csn = machine.Pin(csn_p, machine.Pin.OUT, value=1)
            _ce = machine.Pin(ce_p, machine.Pin.OUT, value=0)
            try:
                machine.SPI(1).deinit()
            except Exception:
                pass
            spi = machine.SPI(
                1, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso
            )
            csn.value(0)
            status = spi.read(2, 0x00)
            csn.value(1)
            status_b, config_b = status[0], status[1]
            if (status_b != 0x00 and status_b != 0xFF) or (config_b != 0x00 and config_b != 0xFF):
                print("🎉 SUCCESS! NRF24 Module Auto-Detected!")
                print("   Pin Mapping Identified: [%s]" % name)
                print("   SCK  = GPIO %d" % sck_p)
                print("   MOSI = GPIO %d" % mosi_p)
                print("   MISO = GPIO %d" % miso_p)
                print("   CSN  = GPIO %d" % csn_p)
                print("   CE   = GPIO %d" % ce_p)
                print("   Status Reg (0x07): 0x%02X" % status_b)
                print("   Config Reg (0x00): 0x%02X\n" % config_b)
                found = True
                break
        except Exception:
            pass
    if not found:
        print("⚠️ No active NRF24 response detected on candidate pins.")
        print("   Ensure 3.3V power (VCC) & GND wires are firmly attached.")


auto_discover_nrf24()
