#!/data/data/com.termux/files/usr/bin/python3
"""
🕵️ Universal 2.4GHz Promiscuous Preamble Sniffer Engine
Uses 2-byte preamble matching (0x55 0x55 / 0xAA 0xAA) with CRC disabled
and channel hopping to intercept frequency-hopping gamepad payloads regardless of MAC address.
"""

import sys
import time

MICROPYTHON_PROMISCUOUS_SCRIPT = """
import machine, time

def promiscuous_hop_sniff(channels=[10, 25, 38, 48, 64, 76], duration_sec=5.0, data_rate_mode='1M'):
    sck = machine.Pin(14, machine.Pin.OUT)
    mosi = machine.Pin(13, machine.Pin.OUT)
    miso = machine.Pin(12, machine.Pin.IN)
    csn = machine.Pin(15, machine.Pin.OUT, value=1)
    ce = machine.Pin(16, machine.Pin.OUT, value=0)

    try: machine.SPI(1).deinit()
    except Exception: pass
    spi = machine.SPI(1, baudrate=4000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

    def w_reg(r, v): csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)
    def w_buf(r, buf): csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)
    def r_reg(r): csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]
    def r_payload(l=16): csn.value(0); rx = spi.read(l + 1, 0x61); csn.value(1); return rx[1:]

    # Configure Promiscuous Sniffer
    w_reg(0x00, 0x03) # PWR_UP=1, PRIM_RX=1, EN_CRC=0 (NO CRC for raw promiscuous capture!)
    w_reg(0x01, 0x00) # Disable Auto-ACK on all pipes
    w_reg(0x02, 0x01) # Enable Pipe 0
    w_reg(0x03, 0x01) # 3-byte Address Width (SETUP_AW = 0x01)
    
    rf_setup = 0x07 # 1Mbps +7dBm Si24R1
    if data_rate_mode == '2M':
        rf_setup = 0x0F # 2Mbps +7dBm
    elif data_rate_mode == '250K':
        rf_setup = 0x27 # 250Kbps +7dBm
    w_reg(0x06, rf_setup)

    w_reg(0x11, 32)   # 32-byte max payload length
    w_buf(0x0A, b'\\x55\\x55\\x55') # Set 3-byte preamble matching address
    w_reg(0x07, 0x70) # Flush status interrupts
    csn.value(0); spi.write(bytes([0xE2])); csn.value(1) # FLUSH_RX
    ce.value(1)

    print('======================================================================')
    print('🕵️ UNIVERSAL PROMISCUOUS PREAMBLE SNIFFER (Data Rate: %s)' % data_rate_mode)
    print('   Hopping Channels: %s' % str(channels))
    print('   PREAMBLE MATCH: 0x55 0x55 | CRC: DISABLED')
    print('   PRESS AND HOLD GAMEPAD BUTTONS / MOVE JOYSTICKS NOW!')
    print('======================================================================\\n')

    start = time.time()
    count = 0
    last_hex = ""

    while time.time() - start < duration_sec:
        for ch in channels:
            w_reg(0x05, ch) # Switch Channel
            time.sleep_ms(8)

            st = r_reg(0x07)
            fifo = r_reg(0x17)

            if (st & 0x40) or ((fifo & 0x01) == 0):
                payload = r_payload(16)
                hex_str = ' '.join(['%02X' % b for b in payload])
                # Filter out pure noise (all 0x00 or all 0xFF)
                if hex_str != last_hex and payload != bytes(16) and payload != b'\\xFF'*16:
                    count += 1
                    bin_bits = ' '.join(['{:08b}'.format(b) for b in payload[:4]])
                    print('CAPTURED FRAME #%03d [CH %2d] | HEX: [%s]' % (count, ch, hex_str))
                    print('                         | BITS: %s' % bin_bits)
                    last_hex = hex_str
                w_reg(0x07, 0x40) # Clear RX_DR flag

    ce.value(0)
    print('\\n======================================================================')
    print('Promiscuous Sniffing Complete. Total valid frames captured: %d' % count)

promiscuous_hop_sniff([10, 25, 38, 48, 64, 76], 3.0, '1M')
"""

def main():
    print("=== Universal Promiscuous Preamble Sniffer Engine Loaded ===")

if __name__ == '__main__':
    main()
