"""vplay - cross-platform host toolkit for the ESP32 + nRF24L01+/Si24R1 2.4GHz gamepad RF lab.

Package layout
--------------
- :mod:`vplay.hostinfo`   - host OS detection (Windows / Linux / macOS / Android-Termux) and console setup
- :mod:`vplay.config`     - single source of truth for pins, device and web settings
- :mod:`vplay.transport`  - byte-level links to the board (pyserial COM/tty port, or raw CP210x over PyUSB on Android)
- :mod:`vplay.repl`       - MicroPython Raw-REPL protocol on top of any transport
- :mod:`vplay.device`     - thread-safe, auto-reconnecting device session used by CLI and web UI
- :mod:`vplay.payloads`   - device-side MicroPython programs (real ``.py`` files) and their registry
- :mod:`vplay.flasher`    - MicroPython firmware flashing via esptool
- :mod:`vplay.terminal`   - interactive REPL terminal (Windows console and POSIX tty)
- :mod:`vplay.web`        - local web control center
- :mod:`vplay.cli`        - ``vplay`` command-line entry point
"""

__version__ = "0.2.0"
