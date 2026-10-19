"""Unified command-line interface for vplay (`vplay` or `python -m vplay`).

Subcommands
-----------
* ``vplay doctor``             inspect host OS, drivers, serial ports, USB devices & board link
* ``vplay presets``            list all built-in MicroPython hardware/RF presets
* ``vplay run <preset>``       execute a built-in preset on the ESP32 with live streaming output
* ``vplay exec <code|-f FILE>`` execute custom MicroPython code or a local .py file on the ESP32
* ``vplay repl``               open an interactive MicroPython REPL terminal
* ``vplay flash [FIRMWARE]``   flash MicroPython firmware onto the ESP32
* ``vplay web``                launch the Web Control Center (http://127.0.0.1:8080)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vplay import __version__, hostinfo
from vplay.config import Config, load_config
from vplay.device import DeviceSession
from vplay.payloads import PRESET_LIST, PRESETS, get_preset
from vplay.transport import BACKENDS, TransportError, resolve_backend
from vplay.transport.serial_port import WINDOWS_DRIVER_HINT, list_serial_ports, probe_windows_pnp


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vplay",
        description="vplay: Cross-Platform 2.4GHz Retro Gamepad RF Sniffer & Emulation Engine",
    )
    parser.add_argument("--version", action="version", version=f"vplay {__version__}")
    parser.add_argument("--config", help="Path to vplay.toml configuration file")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        help="Transport backend: auto (default), serial (COM/tty), or usb (raw CP210x/PyUSB)",
    )
    parser.add_argument("--port", help="Serial port (e.g. COM5 or /dev/ttyUSB0) for serial backend")
    parser.add_argument("--baud", type=int, help="UART baud rate (default: 115200)")

    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("doctor", help="Check host OS, drivers, serial ports, USB devices & board link")
    sub.add_parser("presets", help="List all built-in MicroPython hardware & RF presets")

    p_run = sub.add_parser("run", help="Run a built-in preset on the connected ESP32")
    p_run.add_argument("preset", choices=list(PRESETS.keys()), help="Preset name to execute")
    p_run.add_argument("--timeout", type=float, help="Override execution timeout in seconds")
    p_run.add_argument("--show-code", action="store_true", help="Print the rendered MicroPython code and exit")

    p_exec = sub.add_parser("exec", help="Execute custom MicroPython code or a file on the ESP32")
    p_exec.add_argument("code", nargs="?", help="Inline MicroPython snippet to execute")
    p_exec.add_argument("-f", "--file", help="Path to a local MicroPython .py file to execute")
    p_exec.add_argument("--timeout", type=float, default=30.0, help="Execution timeout in seconds")

    sub.add_parser("repl", help="Open an interactive MicroPython REPL terminal")

    p_flash = sub.add_parser("flash", help="Flash MicroPython firmware onto the ESP32")
    p_flash.add_argument("firmware", nargs="?", help="Path to firmware .bin (default: bundled v1.22.2)")
    p_flash.add_argument("--erase", action="store_true", help="Erase full SPI flash before writing")
    p_flash.add_argument("--flash-baud", type=int, default=460800, help="Flashing baud rate (default: 460800)")

    p_web = sub.add_parser("web", help="Start the local Web Control Center dashboard")
    p_web.add_argument("--bind", help="Bind address (default: 127.0.0.1)")
    p_web.add_argument("--web-port", type=int, help="HTTP port (default: 8080)")

    return parser


def _resolve_config(args: argparse.Namespace) -> Config:
    cfg = load_config(args.config)
    cfg = cfg.replace(
        device={
            "backend": args.backend,
            "port": args.port,
            "baudrate": args.baud,
        },
        web={
            "host": getattr(args, "bind", None),
            "port": getattr(args, "web_port", None),
        },
    )
    return cfg


def _stream_printer(text: str, stream: str) -> None:
    target = sys.stderr if stream == "stderr" else sys.stdout
    target.write(text)
    target.flush()


def cmd_doctor(cfg: Config) -> int:
    backend = resolve_backend(cfg.device.backend)
    print("======================================================================")
    print(f"🩺 vplay Platform & Hardware Diagnostics (v{__version__})")
    print("======================================================================")
    print(f"  Host OS         : {hostinfo.HOST.value} ({sys.platform})")
    print(f"  Python          : {sys.version.split()[0]} ({sys.executable})")
    print(f"  Config Source   : {cfg.source}")
    print(f"  Active Backend  : {backend} (configured: {cfg.device.backend})")
    print(
        f"  NRF24 Pins      : SCK={cfg.pins.sck}, MOSI={cfg.pins.mosi}, MISO={cfg.pins.miso}, "
        f"CSN={cfg.pins.csn}, CE={cfg.pins.ce}, LED={cfg.pins.led}"
    )

    if hostinfo.is_windows():
        pnp = probe_windows_pnp(cfg.device.vid, cfg.device.pid)
        if pnp and pnp.present:
            state = (
                "✅ Driver OK"
                if pnp.problem_code == 0
                else f"⚠️ Driver Missing (PnP Error Code {pnp.problem_code})"
            )
            print(f"  Windows USB PnP : {pnp.description} [{pnp.instance_id}] -> {state}")

    print("\n--- Enumerated Serial Ports (pyserial) ---")
    ports = list_serial_ports()
    if not ports:
        print("  (none detected)")
    else:
        for p in ports:
            tag = "  <-- CP2102 MATCH" if p.is_cp210x else ""
            vid_pid = f"{p.vid:04x}:{p.pid:04x}" if p.vid is not None and p.pid is not None else "n/a"
            print(f"  * {p.device:<12} [{vid_pid}] {p.description}{tag}")

    print("\n--- Probing ESP32 MicroPython Link ---")
    with DeviceSession(cfg) as session:
        try:
            res = session.exec(
                "import sys, machine, ubinascii; "
                "print('  MicroPython     :', sys.version); "
                "print('  CPU Frequency   :', machine.freq() // 1000000, 'MHz'); "
                "print('  Unique Chip ID  :', ubinascii.hexlify(machine.unique_id()).decode())",
                timeout=5.0,
            )
            sys.stdout.write(res.stdout)
            if res.stderr:
                sys.stderr.write(res.stderr)
            print("  Status          : ✅ ONLINE & READY")
            return 0
        except TransportError as exc:
            print(f"  Status          : ❌ OFFLINE ({exc})")
            return 1


def cmd_presets(cfg: Config) -> int:
    print(f"Available vplay presets ({len(PRESET_LIST)}):")
    print("-" * 72)
    for p in PRESET_LIST:
        print(f"  {p.key:<16} {p.title}")
        print(f"  {'':<16} {p.desc}")
    return 0


def cmd_run(cfg: Config, args: argparse.Namespace) -> int:
    preset = get_preset(args.preset)
    code = preset.render(cfg.pins)
    if args.show_code:
        print(code)
        return 0
    timeout = args.timeout if args.timeout is not None else preset.timeout
    try:
        with DeviceSession(cfg) as session:
            res = session.exec(code, timeout=timeout, on_output=_stream_printer)
        if res.timed_out:
            print(f"\n⚠️ Timed out after {timeout:.1f}s (interrupted with Ctrl+C).", file=sys.stderr)
            return 124
        return 0 if res.ok else 1
    except TransportError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


def cmd_exec(cfg: Config, args: argparse.Namespace) -> int:
    if args.file:
        code = Path(args.file).read_text(encoding="utf-8")
    elif args.code:
        code = args.code
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    else:
        print("Pass inline code, --file PATH, or pipe code on stdin.", file=sys.stderr)
        return 2

    try:
        with DeviceSession(cfg) as session:
            res = session.exec(code, timeout=args.timeout, on_output=_stream_printer)
        return 0 if res.ok else 1
    except TransportError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    hostinfo.configure_console()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.subcommand:
        parser.print_help()
        return 0

    try:
        cfg = _resolve_config(args)
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.subcommand == "doctor":
        return cmd_doctor(cfg)
    if args.subcommand == "presets":
        return cmd_presets(cfg)
    if args.subcommand == "run":
        return cmd_run(cfg, args)
    if args.subcommand == "exec":
        return cmd_exec(cfg, args)
    if args.subcommand == "repl":
        from vplay.terminal import run_interactive_repl

        try:
            return run_interactive_repl(cfg.device)
        except TransportError as exc:
            print(f"❌ {exc}", file=sys.stderr)
            return 1
    if args.subcommand == "flash":
        from vplay.flasher import flash_micropython

        try:
            flash_micropython(
                cfg.device,
                args.firmware,
                baudrate=args.flash_baud,
                erase=args.erase,
            )
            return 0
        except (TransportError, FileNotFoundError) as exc:
            print(f"❌ {exc}", file=sys.stderr)
            return 1
    if args.subcommand == "web":
        from vplay.web import run_web_server

        return run_web_server(cfg)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
