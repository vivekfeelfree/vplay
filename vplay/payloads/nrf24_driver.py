import machine
import time

PIN_SCK = globals().get("PIN_SCK", 14)
PIN_MOSI = globals().get("PIN_MOSI", 13)
PIN_MISO = globals().get("PIN_MISO", 12)
PIN_CSN = globals().get("PIN_CSN", 15)
PIN_CE = globals().get("PIN_CE", 16)
SPI_ID = globals().get("SPI_ID", 1)
SPI_BAUDRATE = globals().get("SPI_BAUDRATE", 4000000)


class NRF24Controller:
    CONFIG = 0x00
    EN_AA = 0x01
    EN_RXADDR = 0x02
    SETUP_AW = 0x03
    SETUP_RETR = 0x04
    RF_CH = 0x05
    RF_SETUP = 0x06
    STATUS = 0x07
    OBSERVE_TX = 0x08
    RPD = 0x09
    RX_ADDR_P0 = 0x0A
    RX_ADDR_P1 = 0x0B
    TX_ADDR = 0x10
    RX_PW_P0 = 0x11
    FIFO_STATUS = 0x17
    DYNPD = 0x1C
    FEATURE = 0x1D

    R_REGISTER = 0x00
    W_REGISTER = 0x20
    R_RX_PAYLOAD = 0x61
    W_TX_PAYLOAD = 0xA0
    FLUSH_TX = 0xE1
    FLUSH_RX = 0xE2

    def __init__(self, sck=PIN_SCK, mosi=PIN_MOSI, miso=PIN_MISO, csn=PIN_CSN, ce=PIN_CE):
        self.sck_pin = machine.Pin(sck, machine.Pin.OUT)
        self.mosi_pin = machine.Pin(mosi, machine.Pin.OUT)
        self.miso_pin = machine.Pin(miso, machine.Pin.IN)
        self.csn_pin = machine.Pin(csn, machine.Pin.OUT, value=1)
        self.ce_pin = machine.Pin(ce, machine.Pin.OUT, value=0)
        try:
            machine.SPI(SPI_ID).deinit()
        except Exception:
            pass
        self.spi = machine.SPI(
            SPI_ID,
            baudrate=SPI_BAUDRATE,
            polarity=0,
            phase=0,
            sck=self.sck_pin,
            mosi=self.mosi_pin,
            miso=self.miso_pin,
        )

    def write_reg(self, reg, val):
        self.csn_pin.value(0)
        status = self.spi.read(1, self.W_REGISTER | (reg & 0x1F))
        self.spi.write(bytes([val]))
        self.csn_pin.value(1)
        return status[0]

    def read_reg(self, reg):
        self.csn_pin.value(0)
        res = self.spi.read(2, self.R_REGISTER | (reg & 0x1F))
        self.csn_pin.value(1)
        return res[1]

    def write_buf(self, reg, buf):
        self.csn_pin.value(0)
        self.spi.write(bytes([self.W_REGISTER | (reg & 0x1F)]) + bytes(buf))
        self.csn_pin.value(1)

    def read_buf(self, reg, length):
        self.csn_pin.value(0)
        rx = self.spi.read(length + 1, self.R_REGISTER | (reg & 0x1F))
        self.csn_pin.value(1)
        return rx[1:]

    def set_channel(self, channel):
        self.write_reg(self.RF_CH, channel & 0x7F)

    def set_rf_config(self, data_rate="2M", power_dbm=7):
        rf_setup = 0x00
        if data_rate == "250K":
            rf_setup |= 1 << 5
        elif data_rate == "2M":
            rf_setup |= 1 << 3
        if power_dbm >= 7:
            rf_setup |= 0x07
        elif power_dbm >= 0:
            rf_setup |= 0x06
        elif power_dbm >= -6:
            rf_setup |= 0x04
        else:
            rf_setup |= 0x02
        self.write_reg(self.RF_SETUP, rf_setup)

    def set_address_width(self, width):
        if width not in (3, 4, 5):
            raise ValueError("Address width must be 3, 4, or 5 bytes")
        self.write_reg(self.SETUP_AW, (width - 2) & 0x03)

    def enable_promiscuous_sniffer(self, channel=58, payload_len=32):
        self.ce_pin.value(0)
        self.write_reg(self.CONFIG, 0x03)  # PWR_UP=1, PRIM_RX=1, EN_CRC=0
        self.write_reg(self.EN_AA, 0x00)
        self.write_reg(self.EN_RXADDR, 0x01)
        self.set_address_width(3)
        self.set_channel(channel)
        self.set_rf_config("2M", 7)
        self.write_reg(self.RX_PW_P0, payload_len)
        self.write_buf(self.RX_ADDR_P0, b"\x55\x55\x55")
        self.write_reg(self.STATUS, 0x70)
        self.csn_pin.value(0)
        self.spi.write(bytes([self.FLUSH_RX]))
        self.csn_pin.value(1)
        self.ce_pin.value(1)

    def read_rx_payload(self, length=32):
        self.csn_pin.value(0)
        rx = self.spi.read(length + 1, self.R_RX_PAYLOAD)
        self.csn_pin.value(1)
        self.write_reg(self.STATUS, 0x70)
        return rx[1:]

    def sweep_channels(self, start_ch=0, end_ch=80, delay_ms=8):
        results = []
        for ch in range(start_ch, end_ch + 1):
            self.set_channel(ch)
            time.sleep_ms(delay_ms)
            rpd = self.read_reg(self.RPD) & 0x01
            status = self.read_reg(self.STATUS)
            if rpd or (status & 0x40):
                results.append((ch, rpd, status))
        return results

    def dump_full_diagnostics(self):
        return {
            "CONFIG": hex(self.read_reg(self.CONFIG)),
            "EN_AA": hex(self.read_reg(self.EN_AA)),
            "EN_RXADDR": hex(self.read_reg(self.EN_RXADDR)),
            "SETUP_AW": hex(self.read_reg(self.SETUP_AW)),
            "SETUP_RETR": hex(self.read_reg(self.SETUP_RETR)),
            "RF_CH": hex(self.read_reg(self.RF_CH)),
            "RF_SETUP": hex(self.read_reg(self.RF_SETUP)),
            "STATUS": hex(self.read_reg(self.STATUS)),
            "RPD_CARRIER": self.read_reg(self.RPD) & 0x01,
            "FIFO_STATUS": hex(self.read_reg(self.FIFO_STATUS)),
            "TX_ADDR": [hex(b) for b in self.read_buf(self.TX_ADDR, 5)],
            "RX_ADDR_P0": [hex(b) for b in self.read_buf(self.RX_ADDR_P0, 5)],
        }


nrf = NRF24Controller()
print("=== NRF24Controller Driver Initialized ===")
for k, v in nrf.dump_full_diagnostics().items():
    print("  %-12s : %s" % (k, v))
