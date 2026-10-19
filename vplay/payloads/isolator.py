import machine
import time

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)
SPI_BAUDRATE = globals().get("SPI_BAUDRATE", 4000000)


def run_isolation(channels=None):
    if channels is None:
        channels = [10, 25, 38, 48, 58, 64, 76]
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

    def config_rx(ch):
        ce.value(0)
        w_reg(0x00, 0x03)
        w_reg(0x01, 0x00)
        w_reg(0x02, 0x01)
        w_reg(0x03, 0x01)
        w_reg(0x06, 0x0F)
        w_reg(0x11, 32)
        w_buf(0x0A, b"\x55\x55\x55")
        w_reg(0x05, ch)
        w_reg(0x07, 0x70)
        csn.value(0)
        spi.write(bytes([0xE2]))
        csn.value(1)
        ce.value(1)

    print("======================================================================")
    print("🔬 STEP 1: BASELINE AMBIENT NOISE SCAN (1.5 SECONDS)")
    print("👉 KEEP GAMEPAD IDLE! DO NOT TOUCH BUTTONS YET.")
    print("======================================================================\n")
    base_counts = {}
    for ch in channels:
        config_rx(ch)
        t0 = time.time()
        cnt = 0
        while time.time() - t0 < 0.2:
            st = r_reg(0x07)
            fifo = r_reg(0x17)
            if (st & 0x40) or ((fifo & 0x01) == 0):
                cnt += 1
                w_reg(0x07, 0x40)
            time.sleep_ms(2)
        base_counts[ch] = cnt
        print("   Ch %2d (2.%03d GHz) Idle Noise: %d pkts" % (ch, 400 + ch, cnt))
    print("\n======================================================================")
    print("🔬 STEP 2: ACTIVE CONTROLLER BURST SCAN (1.5 SECONDS)")
    print("👉 PRESS AND HOLD A BUTTON / JOYSTICK NOW!")
    print("======================================================================\n")
    time.sleep(0.5)
    active_counts = {}
    samples = []
    for ch in channels:
        config_rx(ch)
        t0 = time.time()
        cnt = 0
        while time.time() - t0 < 0.25:
            st = r_reg(0x07)
            fifo = r_reg(0x17)
            if (st & 0x40) or ((fifo & 0x01) == 0):
                p = r_payload(32)
                cnt += 1
                if p != bytes(32) and p != b"\xFF" * 32:
                    hex_str = " ".join(["%02X" % b for b in p[:12]])
                    samples.append((ch, hex_str))
                w_reg(0x07, 0x40)
            time.sleep_ms(2)
        active_counts[ch] = cnt
    ce.value(0)
    print("--- DIFFERENTIAL SURGE ANALYSIS ---")
    best_ch = -1
    max_surge = 0
    for ch in channels:
        b = base_counts.get(ch, 0)
        a = active_counts.get(ch, 0)
        surge = a - b
        print("Ch %2d | Idle: %2d | Active: %2d | SURGE: %+2d" % (ch, b, a, surge))
        if surge > max_surge:
            max_surge = surge
            best_ch = ch
    if best_ch != -1 and max_surge >= 3:
        print("\n🎉 GAMEPAD CHANNEL ISOLATED: Channel %d!" % best_ch)
        print("   Payload sample on Channel %d:" % best_ch)
        for c, h in samples:
            if c == best_ch:
                print("   -> HEX: [%s]" % h)
    else:
        print("\n⚠️ No high burst surge above baseline noise. Retry with button held down!")


run_isolation([10, 25, 38, 48, 58, 64, 76])
