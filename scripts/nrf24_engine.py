#!/data/data/com.termux/files/usr/bin/python3
"""
⚡ ESP32 NRF24L01+ / Si24R1 Granular Hardware Control & Sniffer Engine
Provides full register level control, channel sweeping, promiscuous sniffing,
and controller bitmask analysis for reverse-engineering 2.4GHz gamepads.
"""

import sys
import time

# MicroPython Driver Script to be uploaded / injected to ESP32
MICROPYTHON_NRF24_DRIVER = """
import machine, time

class NRF24Controller:
    # NRF24 Register Map Constants
    CONFIG      = 0x00
    EN_AA       = 0x01
    EN_RXADDR   = 0x02
    SETUP_AW    = 0x03
    SETUP_RETR  = 0x04
    RF_CH       = 0x05
    RF_SETUP    = 0x06
    STATUS      = 0x07
    OBSERVE_TX  = 0x08
    RPD         = 0x09
    RX_ADDR_P0  = 0x0A
    RX_ADDR_P1  = 0x0B
    TX_ADDR     = 0x10
    RX_PW_P0    = 0x11
    FIFO_STATUS = 0x17
    DYNPD       = 0x1C
    FEATURE     = 0x1D

    # SPI Commands
    R_REGISTER         = 0x00
    W_REGISTER         = 0x20
    R_RX_PAYLOAD       = 0x61
    W_TX_PAYLOAD       = 0xA0
    FLUSH_TX           = 0xE1
    FLUSH_RX           = 0xE2
    REUSE_TX_PL        = 0xE3
    ACTIVATE           = 0x50
    R_RX_PL_WID        = 0x60
    W_ACK_PAYLOAD      = 0xA8
    W_TX_PAYLOAD_NOACK = 0xB0

    def __init__(self, sck=18, mosi=23, miso=19, csn=5, ce=4):
        self.sck_pin = machine.Pin(sck, machine.Pin.OUT)
        self.mosi_pin = machine.Pin(mosi, machine.Pin.OUT)
        self.miso_pin = machine.Pin(miso, machine.Pin.IN)
        self.csn_pin = machine.Pin(csn, machine.Pin.OUT, value=1)
        self.ce_pin = machine.Pin(ce, machine.Pin.OUT, value=0)
        self.spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0,
                               sck=self.sck_pin, mosi=self.mosi_pin, miso=self.miso_pin)

    def write_reg(self, reg, val):
        self.csn_pin.value(0)
        status = self.spi.read(2, (self.W_REGISTER | (reg & 0x1F)))
        self.spi.write(bytes([val]))
        self.csn_pin.value(1)
        return status[0]

    def read_reg(self, reg):
        self.csn_pin.value(0)
        res = self.spi.read(2, (self.R_REGISTER | (reg & 0x1F)))
        self.csn_pin.value(1)
        return res[1]

    def write_buf(self, reg, buf):
        self.csn_pin.value(0)
        self.spi.write(bytes([(self.W_REGISTER | (reg & 0x1F))]) + bytes(buf))
        self.csn_pin.value(1)

    def read_buf(self, reg, length):
        self.csn_pin.value(0)
        tx = bytes([(self.R_REGISTER | (reg & 0x1F))]) + bytes(length)
        rx = self.spi.read(length + 1, tx[0])
        self.csn_pin.value(1)
        return rx[1:]

    def set_channel(self, channel):
        self.write_reg(self.RF_CH, channel & 0x7F)

    def set_rf_config(self, data_rate='1M', power_dbm=0):
        # Data rate: '250K', '1M', '2M'
        # Si24R1 High Power / NRF24 output power
        rf_setup = 0x00
        if data_rate == '250K':
            rf_setup |= (1 << 5)
        elif data_rate == '2M':
            rf_setup |= (1 << 3)
        # 1M is 0x00

        if power_dbm == 0:
            rf_setup |= 0x06 # 0dBm / high gain
        elif power_dbm == -6:
            rf_setup |= 0x04
        elif power_dbm == -12:
            rf_setup |= 0x02

        self.write_reg(self.RF_SETUP, rf_setup)

    def set_address_width(self, width):
        # 3, 4, or 5 bytes
        val = (width - 2) & 0x03
        self.write_reg(self.SETUP_AW, val)

    def enable_promiscuous_sniffer(self, channel=2, payload_len=16):
        self.ce_pin.value(0)
        self.write_reg(self.CONFIG, 0x0F) # PWR_UP, PRIM_RX, EN_CRC
        self.write_reg(self.EN_AA, 0x00)   # Disable Auto-ACK (Promiscuous)
        self.write_reg(self.EN_RXADDR, 0x01) # Enable Pipe 0
        self.set_address_width(5)
        self.set_channel(channel)
        self.set_rf_config('1M', 0)
        self.write_reg(self.RX_PW_P0, payload_len)
        # Set broadcast promiscuous MAC address
        self.write_buf(self.RX_ADDR_P0, b'\\x55\\x55\\x55\\x55\\x55')
        self.ce_pin.value(1)

    def read_rx_payload(self, length=16):
        self.csn_pin.value(0)
        rx = self.spi.read(length + 1, self.R_RX_PAYLOAD)
        self.csn_pin.value(1)
        # Clear interrupts
        self.write_reg(self.STATUS, 0x70)
        return rx[1:]

    def sweep_channels(self, start_ch=0, end_ch=80, delay_ms=10):
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
        regs = {
            'CONFIG': self.read_reg(self.CONFIG),
            'EN_AA': self.read_reg(self.EN_AA),
            'EN_RXADDR': self.read_reg(self.EN_RXADDR),
            'SETUP_AW': self.read_reg(self.SETUP_AW),
            'SETUP_RETR': self.read_reg(self.SETUP_RETR),
            'RF_CH': self.read_reg(self.RF_CH),
            'RF_SETUP': self.read_reg(self.RF_SETUP),
            'STATUS': self.read_reg(self.STATUS),
            'RPD_CARRIER': self.read_reg(self.RPD) & 0x01,
            'FIFO_STATUS': self.read_reg(self.FIFO_STATUS),
            'TX_ADDR': [hex(b) for b in self.read_buf(self.TX_ADDR, 5)],
            'RX_ADDR_P0': [hex(b) for b in self.read_buf(self.RX_ADDR_P0, 5)]
        }
        return regs
"""

def main():
    print("=== NRF24 Granular Control Engine Loaded ===")
    print("MicroPython Driver ready for deployment to ESP32 over USB OTG.")

if __name__ == '__main__':
    main()
