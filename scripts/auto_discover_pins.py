#!/data/data/com.termux/files/usr/bin/python3
"""
🔍 Automated SPI Pin Discovery Engine for NRF24L01+ / Si24R1 on ESP32
Dynamically scans GPIO pin combinations to auto-detect where the NRF24 transceiver is wired.
"""

import sys
import time

MICROPYTHON_AUTO_DISCOVER_SCRIPT = """
import machine, time

def auto_discover_nrf24():
    print('==================================================')
    print('🔍 AUTOMATED NRF24 SPI PIN DISCOVERY ENGINE')
    print('   Scanning GPIO pins for NRF24/Si24R1 response...')
    print('==================================================\\n')

    # Common pin combinations to test first (fast scan)
    fast_combinations = [
        ('VSPI Standard', 18, 23, 19, 5, 4),
        ('HSPI Standard', 14, 13, 12, 15, 4),
        ('HSPI Alt CSN 5', 14, 13, 12, 5, 4),
        ('VSPI Alt CSN 15', 18, 23, 19, 15, 4),
        ('Header Group 2', 25, 26, 27, 32, 33),
        ('Header Group 3', 27, 14, 12, 13, 15),
    ]

    found = False

    for name, sck_p, mosi_p, miso_p, csn_p, ce_p in fast_combinations:
        try:
            sck = machine.Pin(sck_p, machine.Pin.OUT)
            mosi = machine.Pin(mosi_p, machine.Pin.OUT)
            miso = machine.Pin(miso_p, machine.Pin.IN)
            csn = machine.Pin(csn_p, machine.Pin.OUT, value=1)
            ce = machine.Pin(ce_p, machine.Pin.OUT, value=0)

            spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

            # Read NRF24 CONFIG register (0x00) & STATUS register (0x07)
            csn.value(0)
            status = spi.read(2, 0x00)
            csn.value(1)

            status_byte = status[0]
            config_byte = status[1]

            # Valid NRF24 STATUS reset value has reserved bits 0x0E or RX_EMPTY bit set,
            # and is NOT all 0x00 or all 0xFF.
            if (status_byte != 0x00 and status_byte != 0xFF) or (config_byte != 0x00 and config_byte != 0xFF):
                print('🎉 SUCCESS! NRF24 Module Auto-Detected!')
                print('   Pin Mapping Identified: [%s]' % name)
                print('   SCK  = GPIO %d' % sck_p)
                print('   MOSI = GPIO %d' % mosi_p)
                print('   MISO = GPIO %d' % miso_p)
                print('   CSN  = GPIO %d' % csn_p)
                print('   CE   = GPIO %d' % ce_p)
                print('   Status Reg (0x07): 0x%02X' % status_byte)
                print('   Config Reg (0x00): 0x%02X\\n' % config_byte)
                found = True
                break
        except Exception as e:
            pass

    if not found:
        print('⚠️ No active NRF24 response detected on candidate pins.')
        print('   Ensure 3.3V power (VCC) & GND wires are firmly attached.')

auto_discover_nrf24()
"""

def main():
    print("=== Auto-Discovery Engine Ready ===")

if __name__ == '__main__':
    main()
