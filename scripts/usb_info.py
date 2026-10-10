#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import usb.core
import usb.backend.libusb1 as libusb1

def main():
    print("=== Termux USB Device Diagnostics ===")
    fd = None
    if 'TERMUX_USB_FD' in os.environ:
        fd = int(os.environ['TERMUX_USB_FD'])
        print(f"Received TERMUX_USB_FD: {fd}")
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        fd = int(sys.argv[1])
        print(f"Received FD via argv[1]: {fd}")
    
    # Initialize libusb backend pointing to Termux libusb library
    backend = libusb1.get_backend(find_library=lambda x: '/data/data/com.termux/files/usr/lib/libusb-1.0.so')
    if not backend:
        print("Error: Could not load libusb-1.0 backend")
        sys.exit(1)
        
    print("Libusb backend loaded successfully.")
    
    devices = list(usb.core.find(find_all=True, backend=backend))
    print(f"Found {len(devices)} USB device(s) via PyUSB/libusb.")
    
    for i, dev in enumerate(devices):
        vid = hex(dev.idVendor)
        pid = hex(dev.idProduct)
        print(f"\n--- Device {i+1} ---")
        print(f"  Vendor ID : {vid}")
        print(f"  Product ID: {pid}")
        try:
            mfg = dev.manufacturer
            prod = dev.product
            serial = dev.serial_number
            print(f"  Manufacturer : {mfg}")
            print(f"  Product Name : {prod}")
            print(f"  Serial Number: {serial}")
        except Exception as e:
            print(f"  String Descriptors: {e}")

if __name__ == '__main__':
    main()
