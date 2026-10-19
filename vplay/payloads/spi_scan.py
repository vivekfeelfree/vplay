import machine

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)


def scan_bus(bus_name, sck_p, mosi_p, miso_p, csn_p, ce_p):
    print("=== SCANNING %s PIN CONFIGURATION ===" % bus_name)
    print(
        "Pins: SCK=D%d, MOSI=D%d, MISO=D%d, CSN=D%d, CE=D%d"
        % (sck_p, mosi_p, miso_p, csn_p, ce_p)
    )
    sck = machine.Pin(sck_p, machine.Pin.OUT)
    mosi = machine.Pin(mosi_p, machine.Pin.OUT)
    miso = machine.Pin(miso_p, machine.Pin.IN)
    csn = machine.Pin(csn_p, machine.Pin.OUT, value=1)
    _ce = machine.Pin(ce_p, machine.Pin.OUT, value=0)
    try:
        machine.SPI(SPI_ID).deinit()
    except Exception:
        pass
    spi = machine.SPI(SPI_ID, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

    def r_reg(r):
        csn.value(0)
        res = spi.read(2, r & 0x1F)
        csn.value(1)
        return res[1]

    def r_buf(r, length):
        csn.value(0)
        rx = spi.read(length + 1, r & 0x1F)
        csn.value(1)
        return rx[1:]

    regs = [
        ("CONFIG", 0x00),
        ("EN_AA", 0x01),
        ("EN_RXADDR", 0x02),
        ("SETUP_AW", 0x03),
        ("SETUP_RETR", 0x04),
        ("RF_CH", 0x05),
        ("RF_SETUP", 0x06),
        ("STATUS", 0x07),
    ]
    for name, addr in regs:
        val = r_reg(addr)
        print("  %-10s (0x%02X): 0x%02X (bin: %s)" % (name, addr, val, bin(val)))
    tx_addr = r_buf(0x10, 5)
    print("  TX_ADDR    (0x10): %s\n" % (" ".join(["0x%02X" % b for b in tx_addr])))


scan_bus("Configured Bus (HSPI)", PIN_SCK, PIN_MOSI, PIN_MISO, PIN_CSN, PIN_CE)
if (PIN_SCK, PIN_MOSI, PIN_MISO, PIN_CSN) != (18, 23, 19, 5):
    scan_bus("VSPI (Alternate)", 18, 23, 19, 5, 4)
