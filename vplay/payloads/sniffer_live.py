import machine
import time

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)


def sniff_gamepad_packets(ch=58, duration_sec=3.0):
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

    ce.value(0)
    w_reg(0x00, 0x03)  # PWR_UP, PRIM_RX, EN_CRC=0
    w_reg(0x01, 0x00)  # Disable Auto-ACK
    w_reg(0x02, 0x01)  # Enable Pipe 0
    w_reg(0x03, 0x01)  # 3-byte address width
    w_reg(0x05, ch)
    w_reg(0x06, 0x0F)
    w_reg(0x11, 32)
    w_buf(0x0A, b"\x55\x55\x55")
    w_reg(0x07, 0x70)
    csn.value(0)
    spi.write(bytes([0xE2]))
    csn.value(1)
    ce.value(1)
    print("======================================================================")
    print("🎮 LIVE 2.4GHz GAMEPAD PACKET SNIFFER ACTIVE (Channel %d)" % ch)
    print("   Listening for wireless controller packets for %.1f seconds..." % duration_sec)
    print("======================================================================\n")
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
                print("FRAME #%03d | HEX: [%s]" % (count, hex_str))
                print("          | BITS: %s" % bin_bits)
                last_hex = hex_str
            w_reg(0x07, 0x40)
        time.sleep_ms(5)
    ce.value(0)
    print("\n======================================================================")
    print("Sniffing finished. Total unique payload state frames captured: %d" % count)


sniff_gamepad_packets(58, 3.0)
