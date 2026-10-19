import machine

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)

sck = machine.Pin(PIN_SCK, machine.Pin.OUT)
mosi = machine.Pin(PIN_MOSI, machine.Pin.OUT)
miso = machine.Pin(PIN_MISO, machine.Pin.IN)
csn = machine.Pin(PIN_CSN, machine.Pin.OUT, value=1)
ce = machine.Pin(PIN_CE, machine.Pin.OUT, value=0)
try:
    machine.SPI(SPI_ID).deinit()
except Exception:
    pass
spi = machine.SPI(SPI_ID, baudrate=1000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)


def w_reg(r, v):
    csn.value(0)
    spi.write(bytes([0x20 | (r & 0x1F), v]))
    csn.value(1)


ce.value(0)
w_reg(0x00, 0x0F)  # PWR_UP, PRIM_RX
w_reg(0x01, 0x00)  # Disable Auto-ACK
w_reg(0x02, 0x01)  # Enable Pipe 0
w_reg(0x03, 0x03)  # 5-byte address width
w_reg(0x05, 0x02)  # CH 2 (2402 MHz)
w_reg(0x06, 0x07)  # 1Mbps, +7dBm
w_reg(0x11, 16)    # 16-byte payload
ce.value(1)
print("=== 2.4GHz PROMISCUOUS SNIFFER ACTIVATED ===")
print("Listening on 2402 MHz (Channel 2)...")
