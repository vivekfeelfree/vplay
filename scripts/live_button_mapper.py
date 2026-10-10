#!/data/data/com.termux/files/home/trials/vplay/usr/bin/python3
"""
🎮 Live Controller Button Bitmask Analyzer & Decoder Engine
Captures promiscuous 2.4GHz RF frames on active channels and decodes 
which specific byte and bit position changes when buttons are pressed.
"""

import sys
import time

MICROPYTHON_BUTTON_MAPPER = """
import machine, time

def run_button_mapper(ch=58, duration_sec=5.0):
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
    def r_payload(l=32): csn.value(0); rx = spi.read(l + 1, 0x61); csn.value(1); return rx[1:]

    # Configure Promiscuous RX on Channel
    ce.value(0)
    w_reg(0x00, 0x03) # PWR_UP=1, PRIM_RX=1, EN_CRC=0
    w_reg(0x01, 0x00) # Disable Auto-ACK
    w_reg(0x02, 0x01) # Enable Pipe 0
    w_reg(0x03, 0x01) # 3-byte Address Width
    w_reg(0x06, 0x0F) # 2Mbps
    w_reg(0x11, 32)   # 32-byte payload
    w_buf(0x0A, b'\\x55\\x55\\x55') # Preamble match
    w_reg(0x05, ch)
    w_reg(0x07, 0x70)
    csn.value(0); spi.write(bytes([0xE2])); csn.value(1)
    ce.value(1)

    print("======================================================================")
    print("🎯 LIVE BUTTON BITMASK MAPPER ACTIVE (Channel %d)" % ch)
    print("👉 Press a SINGLE button repeatedly (e.g. 'A', 'B', or 'DOWN')")
    print("======================================================================\\n")

    start = time.time()
    last_payload = None
    count = 0

    while time.time() - start < duration_sec:
        st = r_reg(0x07)
        fifo = r_reg(0x17)
        if (st & 0x40) or ((fifo & 0x01) == 0):
            p = r_payload(32)
            if p != bytes(32) and p != b'\\xFF'*32:
                if last_payload is not None:
                    # Find byte diffs
                    diffs = []
                    for idx in range(min(16, len(p))):
                        if p[idx] != last_payload[idx]:
                            diffs.append("Byte[%d]: 0x%02X -> 0x%02X" % (idx, last_payload[idx], p[idx]))
                    
                    if diffs:
                        count += 1
                        hex_str = ' '.join(['%02X' % b for b in p[:12]])
                        bits_str = ' '.join(['{:08b}'.format(b) for b in p[:4]])
                        print("CHANGE #%02d | %s" % (count, ' | '.join(diffs)))
                        print("          | HEX:  [%s]" % hex_str)
                        print("          | BITS: %s\\n" % bits_str)
                last_payload = p
            w_reg(0x07, 0x40)
        time.sleep_ms(5)

    ce.value(0)
    print("Live Button Mapping session finished. Captured %d state changes." % count)

run_button_mapper(58, 4.0)
"""

def main():
    print("=== Live Controller Button Mapper Script Ready ===")

if __name__ == '__main__':
    main()
