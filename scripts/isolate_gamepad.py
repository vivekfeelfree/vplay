#!/data/data/com.termux/files/usr/bin/python3
"""
🎮 Gamepad Signal Isolator & Ambient Noise Filter Engine
Uses 2-phase differential analysis (Idle Baseline vs Active Button Press)
to isolate the gamepad's exact RF channel and payload signature from ambient 2.4GHz noise (Wi-Fi/Bluetooth).
"""

import sys
import time

MICROPYTHON_ISOLATOR_SCRIPT = """
import machine, time

def run_gamepad_isolation_test(channels=[10, 25, 38, 48, 58, 64, 76]):
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

    def configure_rx(ch, mode_2m=True):
        ce.value(0)
        w_reg(0x00, 0x03) # PWR_UP=1, PRIM_RX=1, EN_CRC=0
        w_reg(0x01, 0x00) # Disable Auto-ACK
        w_reg(0x02, 0x01) # Pipe 0
        w_reg(0x03, 0x01) # 3-byte address width
        w_reg(0x06, 0x0F if mode_2m else 0x07) # 2Mbps / 1Mbps
        w_reg(0x11, 32)
        w_buf(0x0A, b'\\x55\\x55\\x55')
        w_reg(0x05, ch)
        w_reg(0x07, 0x70)
        csn.value(0); spi.write(bytes([0xE2])); csn.value(1)
        ce.value(1)

    print("======================================================================")
    print("🔬 GAMEPAD DIFFERENTIAL ISOLATION TEST")
    print("   PHASE 1: BASELINE NOISE SCAN (3 SECONDS)")
    print("👉 DO NOT PRESS ANY BUTTONS ON THE GAMEPAD NOW! KEEP GAMEPAD IDLE.")
    print("======================================================================\\n")

    baseline_noise = {}
    
    for ch in channels:
        configure_rx(ch)
        t0 = time.time()
        pkt_count = 0
        while time.time() - t0 < 0.4:
            st = r_reg(0x07)
            fifo = r_reg(0x17)
            if (st & 0x40) or ((fifo & 0x01) == 0):
                pkt_count += 1
                w_reg(0x07, 0x40)
            time.sleep_ms(2)
        baseline_noise[ch] = pkt_count
        print("   Channel %2d (2.%03d GHz) Baseline Ambient Noise: %d packets/0.4s" % (ch, 400+ch, pkt_count))

    print("\\n======================================================================")
    print("   PHASE 2: ACTIVE BUTTON PRESS SCAN (4 SECONDS)")
    print("👉 NOW! PRESS AND HOLD THE 'A' BUTTON (OR D-PAD DOWN) CONTINUOUSLY!")
    print("======================================================================\\n")
    
    time.sleep(1.0) # Brief pause before phase 2
    active_press = {}
    active_samples = []

    for ch in channels:
        configure_rx(ch)
        t0 = time.time()
        pkt_count = 0
        while time.time() - t0 < 0.5:
            st = r_reg(0x07)
            fifo = r_reg(0x17)
            if (st & 0x40) or ((fifo & 0x01) == 0):
                p = r_payload(32)
                pkt_count += 1
                if p != bytes(32) and p != b'\\xFF'*32:
                    hex_str = ' '.join(['%02X' % b for b in p[:12]])
                    active_samples.append((ch, hex_str))
                w_reg(0x07, 0x40)
            time.sleep_ms(2)
        active_press[ch] = pkt_count

    print("\\n======================================================================")
    print("📊 DIFFERENTIAL ANALYSIS RESULTS")
    print("======================================================================")
    
    gamepad_candidates = []
    for ch in channels:
        base = baseline_noise.get(ch, 0)
        act = active_press.get(ch, 0)
        diff = act - base
        print("Channel %2d | Baseline Idle: %2d pkts | Active Press: %2d pkts | DELTA: %+2d" % (ch, base, act, diff))
        if diff >= 3:
            gamepad_candidates.append((ch, diff))

    if gamepad_candidates:
        best_ch = max(gamepad_candidates, key=lambda x: x[1])[0]
        print("\\n🎉 HIGH CONFIDENCE MATCH: Controller active channel identified as CH %d!" % best_ch)
        print("   Samples captured during button press on CH %d:" % best_ch)
        for c, h in active_samples:
            if c == best_ch:
                print("   -> HEX: [%s]" % h)
    else:
        print("\\n⚠️ No channel showed significant surge above ambient Wi-Fi noise.")
        print("👉 Check controller power LED / battery state or bring controller closer to NRF24 antenna!")

run_gamepad_isolation_test([10, 25, 38, 48, 58, 64, 76])
"""

def main():
    print("=== Gamepad Signal Isolator Script Loaded ===")

if __name__ == '__main__':
    main()
