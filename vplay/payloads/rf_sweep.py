import machine
import time

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)


def sweep_and_sniff(duration_sec=3.0):
    sck = machine.Pin(PIN_SCK, machine.Pin.OUT)
    mosi = machine.Pin(PIN_MOSI, machine.Pin.OUT)
    miso = machine.Pin(PIN_MISO, machine.Pin.IN)
    csn = machine.Pin(PIN_CSN, machine.Pin.OUT, value=1)
    ce = machine.Pin(PIN_CE, machine.Pin.OUT, value=0)
    try:
        machine.SPI(SPI_ID).deinit()
    except Exception:
        pass
    spi = machine.SPI(SPI_ID, baudrate=2000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

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
    print("📡 STEP 1: SCANNING ALL 80 RF CHANNELS FOR GAMEPAD CARRIER SIGNALS...")
    print("   KEEP PRESSING BUTTONS ON YOUR CONTROLLER REPEATEDLY NOW!")
    print("======================================================================\n")
    active_chs = {}
    ce.value(0)
    w_reg(0x00, 0x0F)
    w_reg(0x01, 0x00)
    w_reg(0x02, 0x01)
    w_reg(0x03, 0x03)
    w_reg(0x06, 0x0F)
    w_reg(0x11, 16)
    w_buf(0x0A, b"\xE7\xE7\xE7\xE7\xE7")
    ce.value(1)
    for ch in range(0, 81, 2):
        w_reg(0x05, ch)
        time.sleep_ms(8)
        rpd = r_reg(0x09) & 0x01
        st = r_reg(0x07)
        if rpd or (st & 0x40):
            active_chs[ch] = active_chs.get(ch, 0) + 1
            w_reg(0x07, 0x40)
    if active_chs:
        print("🎉 Active RF Channels Detected:", active_chs)
        best_ch = max(active_chs, key=active_chs.get)
        print(
            "   Locking onto Active Controller Channel %d (2.%03d GHz)...\n"
            % (best_ch, 400 + best_ch)
        )
    else:
        print("⚠️ No strong carrier burst on channel sweep. Defaulting to CH 38 (2438 MHz)...\n")
        best_ch = 38
    print("======================================================================")
    print("🎮 STEP 2: PROMISCUOUS PACKET INTERCEPTOR LOCKED ON CHANNEL %d" % best_ch)
    print("   Listening for raw wireless frames (CRC OFF, 3-byte Preamble Match)...")
    print("   PRESS AND HOLD GAMEPAD BUTTONS NOW!")
    print("======================================================================\n")
    ce.value(0)
    w_reg(0x00, 0x03)  # PWR_UP=1, PRIM_RX=1, NO_CRC
    w_reg(0x01, 0x00)  # Disable Auto-ACK
    w_reg(0x02, 0x01)  # Enable Pipe 0
    w_reg(0x03, 0x01)  # 3-byte Address Width
    w_reg(0x06, 0x0F)  # 2Mbps
    w_reg(0x11, 32)    # 32-byte max payload
    w_buf(0x0A, b"\x55\x55\x55")  # 3-byte 0x55 preamble match
    w_reg(0x05, best_ch)
    w_reg(0x07, 0x70)
    csn.value(0)
    spi.write(bytes([0xE2]))
    csn.value(1)
    ce.value(1)
    start = time.time()
    count = 0
    last_hex = ""
    while time.time() - start < duration_sec:
        st = r_reg(0x07)
        fifo = r_reg(0x17)
        if (st & 0x40) or ((fifo & 0x01) == 0):
            payload = r_payload(32)
            hex_str = " ".join(["%02X" % b for b in payload[:16]])
            if hex_str != last_hex and payload != bytes(32) and payload != b"\xFF" * 32:
                count += 1
                bin_bits = " ".join(["{:08b}".format(b) for b in payload[:4]])
                print("FRAME #%03d [CH %2d] | HEX: [%s]" % (count, best_ch, hex_str))
                print("                         | BITS: %s" % bin_bits)
                last_hex = hex_str
            w_reg(0x07, 0x40)
        time.sleep_ms(5)
    ce.value(0)
    print("\nPromiscuous Sniffing Complete. Total valid frames captured: %d" % count)


sweep_and_sniff(3.0)
