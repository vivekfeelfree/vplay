import machine
import time

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)
SPI_BAUDRATE = globals().get("SPI_BAUDRATE", 4000000)


def run_live_rf_exercise():
    sck = machine.Pin(PIN_SCK, machine.Pin.OUT)
    mosi = machine.Pin(PIN_MOSI, machine.Pin.OUT)
    miso = machine.Pin(PIN_MISO, machine.Pin.IN)
    csn = machine.Pin(PIN_CSN, machine.Pin.OUT, value=1)
    ce = machine.Pin(PIN_CE, machine.Pin.OUT, value=0)
    try:
        machine.SPI(SPI_ID).deinit()
    except Exception:
        pass
    spi = machine.SPI(
        SPI_ID, baudrate=SPI_BAUDRATE, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso
    )

    def w_reg(r, v):
        csn.value(0)
        spi.write(bytes([0x20 | (r & 0x1F), v]))
        csn.value(1)

    def w_buf(r, buf):
        csn.value(0)
        spi.write(bytes([0x20 | (r & 0x1F)]) + bytes(buf))
        csn.value(1)

    def r_reg(r):
        csn.value(0)
        res = spi.read(2, r & 0x1F)
        csn.value(1)
        return res[1]

    def r_payload(length=32):
        csn.value(0)
        rx = spi.read(length + 1, 0x61)
        csn.value(1)
        return rx[1:]

    print("======================================================================")
    print("📡 LIVE EXERCISE PHASE 1: REAL-TIME CARRIER SPECTRUM SCANNER (8 sec)")
    print("👉 ACTION REQUIRED: PRESS AND HOLD 'DOWN' OR 'A' BUTTON CONTINUOUSLY!")
    print("======================================================================\n")

    ce.value(0)
    w_reg(0x00, 0x0F)
    w_reg(0x01, 0x00)
    w_reg(0x02, 0x01)
    w_reg(0x03, 0x03)
    w_reg(0x06, 0x0F)
    ce.value(1)

    rpd_counts = {}
    scan_start = time.time()
    while time.time() - scan_start < 8.0:
        for ch in range(0, 81, 2):
            w_reg(0x05, ch)
            time.sleep_us(250)
            rpd = r_reg(0x09) & 0x01
            st = r_reg(0x07)
            if rpd or (st & 0x40):
                rpd_counts[ch] = rpd_counts.get(ch, 0) + 1
                w_reg(0x07, 0x40)

    print("--- SPECTRUM CARRIER SCAN RESULTS ---")
    if not rpd_counts:
        print("⚠️ No RF carrier bursts detected! Using fallback channels [10, 25, 38, 48, 58, 64, 76]")
        active_channels = [38, 48, 58, 10, 25, 64, 76]
    else:
        sorted_chs = sorted(rpd_counts.items(), key=lambda x: x[1], reverse=True)
        print("Detected RF Carrier Activity on Channels:")
        for ch, cnt in sorted_chs[:6]:
            bar = "#" * min(cnt, 25)
            print("  Channel %2d (2.%03d GHz) : %-25s (%d bursts)" % (ch, 400 + ch, bar, cnt))
        active_channels = [ch for ch, _ in sorted_chs[:6]]

    print("\n======================================================================")
    print("🕵️ LIVE EXERCISE PHASE 2: MULTI-ADDRESS & RATE PROMISCUOUS MATRIX SCAN")
    print("👉 ACTION REQUIRED: KEEP PRESSING BUTTONS (A, B, D-PAD) ON GAMEPAD!")
    print("======================================================================\n")

    matrix_configs = [
        ("1M-Preamble-55", 0x07, 0x01, b"\x55\x55\x55", 0x03),
        ("2M-Preamble-55", 0x0F, 0x01, b"\x55\x55\x55", 0x03),
        ("1M-Preamble-AA", 0x07, 0x01, b"\xAA\xAA\xAA", 0x03),
        ("2M-Preamble-AA", 0x0F, 0x01, b"\xAA\xAA\xAA", 0x03),
        ("1M-NullAddr-00", 0x07, 0x03, b"\x00\x00\x00\x00\x00", 0x03),
        ("2M-NullAddr-00", 0x0F, 0x03, b"\x00\x00\x00\x00\x00", 0x03),
        ("1M-LT8920-Def", 0x07, 0x03, b"\x61\x62\x63\x64\x65", 0x03),
        ("2M-Retro-ASIC", 0x0F, 0x03, b"\x34\x43\x10\x10\x01", 0x03),
        ("1M-CRC-Default", 0x07, 0x03, b"\xE7\xE7\xE7\xE7\xE7", 0x0F),
    ]

    captured_frames = []
    for label, rf_setup, aw, addr_buf, cfg in matrix_configs:
        print("Testing Matrix Config [%-15s] on channels %s..." % (label, str(active_channels)))
        ce.value(0)
        w_reg(0x00, cfg)
        w_reg(0x01, 0x00)
        w_reg(0x02, 0x01)
        w_reg(0x03, aw)
        w_reg(0x06, rf_setup)
        w_reg(0x11, 32)
        w_buf(0x0A, addr_buf)
        w_reg(0x07, 0x70)
        csn.value(0)
        spi.write(bytes([0xE2]))
        csn.value(1)
        ce.value(1)

        t0 = time.time()
        while time.time() - t0 < 1.2:
            for ch in active_channels:
                w_reg(0x05, ch)
                time.sleep_ms(6)
                st = r_reg(0x07)
                fifo = r_reg(0x17)
                if (st & 0x40) or ((fifo & 0x01) == 0):
                    p = r_payload(32)
                    hex_str = " ".join(["%02X" % b for b in p[:16]])
                    if p != bytes(32) and p != b"\xFF" * 32:
                        print("  🎉 [SUCCESS] CAPTURED FRAME with [%s] on CH %d!" % (label, ch))
                        print("      HEX: [%s]" % hex_str)
                        print("      BITS: %s" % " ".join(["{:08b}".format(b) for b in p[:4]]))
                        captured_frames.append((label, ch, hex_str))
                    w_reg(0x07, 0x40)

    ce.value(0)
    print("\n======================================================================")
    print("🏆 LIVE EXERCISE RESULTS SUMMARY")
    print("======================================================================")
    if captured_frames:
        print("SUCCESS! Captured %d wireless gamepad frames over the air!" % len(captured_frames))
        for item in captured_frames:
            print(" -> Config: %s | Channel: %d | Hex: %s" % item)
    else:
        print("⚠️ No direct frames matched standard preambles.")
        print("👉 Recommended next action: Inspect chip marking on gamepad receiver/stick!")


run_live_rf_exercise()
