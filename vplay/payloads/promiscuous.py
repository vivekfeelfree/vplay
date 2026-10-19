import machine
import time

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)
SPI_BAUDRATE = globals().get("SPI_BAUDRATE", 4000000)


def promiscuous_hop_sniff(channels=None, duration_sec=3.0, data_rate_mode="2M"):
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

    ce.value(0)
    w_reg(0x00, 0x03)  # PWR_UP=1, PRIM_RX=1, EN_CRC=0
    w_reg(0x01, 0x00)  # Disable Auto-ACK
    w_reg(0x02, 0x01)  # Enable Pipe 0
    w_reg(0x03, 0x01)  # 3-byte Address Width (SETUP_AW = 0x01, valid per nRF24 spec)
    rf_setup = 0x0F if data_rate_mode == "2M" else (0x27 if data_rate_mode == "250K" else 0x07)
    w_reg(0x06, rf_setup)
    w_reg(0x11, 32)
    w_buf(0x0A, b"\x55\x55\x55")
    w_reg(0x07, 0x70)
    csn.value(0)
    spi.write(bytes([0xE2]))
    csn.value(1)
    ce.value(1)
    print("======================================================================")
    print("🕵️ UNIVERSAL PROMISCUOUS PREAMBLE SNIFFER ACTIVE (%s)" % data_rate_mode)
    print(
        "   Hopping Channels: %s | Preamble Match: 0x55 0x55 0x55 | CRC: OFF"
        % str(channels)
    )
    print("   PRESS AND HOLD GAMEPAD BUTTONS NOW!")
    print("======================================================================\n")
    start = time.time()
    count = 0
    last_hex = ""
    while time.time() - start < duration_sec:
        for ch in channels:
            w_reg(0x05, ch)
            time.sleep_ms(8)
            st = r_reg(0x07)
            fifo = r_reg(0x17)
            if (st & 0x40) or ((fifo & 0x01) == 0):
                payload = r_payload(32)
                hex_str = " ".join(["%02X" % b for b in payload[:16]])
                if hex_str != last_hex and payload != bytes(32) and payload != b"\xFF" * 32:
                    count += 1
                    bin_bits = " ".join(["{:08b}".format(b) for b in payload[:4]])
                    print("FRAME #%03d [CH %2d] | HEX: [%s]" % (count, ch, hex_str))
                    print("                         | BITS: %s" % bin_bits)
                    last_hex = hex_str
                w_reg(0x07, 0x40)
    ce.value(0)
    print("\nPromiscuous Sniffing Complete. Total valid frames captured: %d" % count)


promiscuous_hop_sniff([10, 25, 38, 48, 58, 64, 76], 3.0, "2M")
