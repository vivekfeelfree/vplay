"""Cross-platform interactive MicroPython REPL terminal.

Replaces the POSIX-only ``select.select([sys.stdin], ...)`` loop in the original
``scripts/repl_cli.py`` (which raises ``OSError: [WinError 10038]`` on Windows) with a
daemon reader thread + queue that works identically on Windows, Linux, macOS, and
Android/Termux.
"""

from __future__ import annotations

import queue
import sys
import threading

from vplay import hostinfo
from vplay.config import DeviceConfig
from vplay.transport import open_transport


def run_interactive_repl(device_cfg: DeviceConfig) -> int:
    """Open an interactive line-oriented MicroPython REPL session over the configured transport."""
    hostinfo.configure_console()
    print("==================================================", flush=True)
    print("🚀 vplay Interactive MicroPython REPL Terminal", flush=True)
    print("   Type any Python expression/statement and press Enter.")
    print("   Press Ctrl+C or type 'exit()' to return to shell.", flush=True)
    print("==================================================\n", flush=True)

    with open_transport(device_cfg) as transport:
        print(f"Connected: {transport.description}\n", flush=True)
        # Ensure we are in friendly REPL mode (Ctrl-B) and print a fresh prompt.
        transport.write(b"\x03\x03\x02\r\n")

        lines: queue.Queue[str | None] = queue.Queue()

        def _stdin_reader() -> None:
            try:
                for line in sys.stdin:
                    lines.put(line)
            except Exception:
                pass
            finally:
                lines.put(None)

        reader = threading.Thread(target=_stdin_reader, name="vplay-stdin", daemon=True)
        reader.start()

        try:
            while True:
                rx = transport.read(512, timeout=0.03)
                if rx:
                    sys.stdout.write(rx.decode("utf-8", errors="replace"))
                    sys.stdout.flush()
                try:
                    line = lines.get_nowait()
                except queue.Empty:
                    continue
                if line is None or line.strip() == "exit()":
                    print("\nExiting REPL terminal...", flush=True)
                    break
                payload = line.rstrip("\r\n") + "\r\n"
                transport.write(payload.encode("utf-8"))
        except KeyboardInterrupt:
            print("\nExiting REPL terminal...", flush=True)
    return 0
