#!/data/data/com.termux/files/usr/bin/python3
"""
🎮 2.4GHz Gamepad RF Packet Sniffer & Bitmask Analyzer Engine
Captures raw un-encrypted 2.4GHz wireless frames from retro gamepad controllers
over NRF24L01+/Si24R1 transceiver and prints bitmask state changes in real time.
"""

import sys
import time

MICROPYTHON_SNIFFER_SCRIPT = """
import machine, time

def sniff_gamepad_packets(ch=2, duration_sec=8):
    sck = machine.Pin(14, machine.Pin.OUT)
    mosi = machine.Pin(13, machine.Pin.OUT)
    miso = machine.Pin(12, machine.Pin.IN)
    csn = machine.Pin(15, machine.Pin.OUT, value=1)
    ce = machine.Pin(16, machine.Pin.OUT, value=0)

    try: machine.SPI(1).deinit()
    except Exception: pass
    spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

    def w_reg(r, v):
        csn.value(0); spi.write(bytes([0x20|(r&0x1F), v])); csn.value(1)

    def w_buf(r, buf):
        csn.value(0); spi.write(bytes([0x20|(r&0x1F)]) + bytes(buf)); csn.value(1)

    def r_reg(r):
        csn.value(0); res = spi.read(2, r & 0x1F); csn.value(1); return res[1]

    def r_payload(length=16):
        csn.value(0); rx = spi.read(length + 1, 0x61); csn.value(1); return rx[1:]

    # Configure NRF24 for RX Packet Capture
    ce.value(0)
    w_reg(0x00, 0x0F) # PWR_UP, PRIM_RX, EN_CRC
    w_reg(0x01, 0x00) # Disable Auto-ACK (Promiscuous)
    w_reg(0x02, 0x01) # Enable Pipe 0
    w_reg(0x03, 0x03) # 5-byte address width
    w_reg(0x05, ch)   # Channel 2 (2402 MHz)
    w_reg(0x06, 0x0F) # 2Mbps / 1Mbps +7dBm
    w_reg(0x11, 16)   # 16-byte payload
    w_buf(0x0A, b'\\xE7\\xE7\\xE7\\xE7\\xE7')
    w_reg(0x07, 0x70) # Clear interrupts
    csn.value(0); spi.write(bytes([0xE2])); csn.value(1) # FLUSH_RX
    ce.value(1)

    print('======================================================================')
    print('🎮 LIVE 2.4GHz GAMEPAD PACKET SNIFFER ACTIVE (Channel %d)' % ch)
    print('   Listening for wireless controller packets for %d seconds...' % duration_sec)
    print('   Press buttons / move joysticks on your gamepad NOW!')
    print('======================================================================\\n')

    start = time.time()
    count = 0
    last_hex = ""
    while time.time() - start < duration_sec:
        st = r_reg(0x07)
        fifo = r_reg(0x17)
        if (st & 0x40) or ((fifo & 0x01) == 0):
            payload = r_payload(16)
            hex_str = ' '.join(['%02X' % b for b in payload])
            if hex_str != last_hex:
                count += 1
                bin_bits = ' '.join(['{:08b}'.format(b) for b in payload[:4]])
                print('FRAME #%03d | HEX: [%s]' % (count, hex_str))
                print('          | BITS: %s' % bin_bits)
                last_hex = hex_str
            w_reg(0x07, 0x40) # Clear RX interrupt
        time.sleep_ms(5)

    ce.value(0)
    print('\\n======================================================================')
    print('Sniffing finished. Total unique payload state frames captured: %d' % count)

sniff_gamepad_packets(2, 8)
"""

def main():
    print("=== 2.4GHz Gamepad RF Sniffer Engine Loaded ===")

if __name__ == '__main__':
    main()
