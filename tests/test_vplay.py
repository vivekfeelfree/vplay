"""Automated test suite covering config, transport selection, RawRepl protocol, payloads, web API, and CLI."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from vplay import hostinfo
from vplay.config import Config, Pins, load_config
from vplay.device import DeviceSession
from vplay.payloads import PRESET_LIST, PRESETS, get_preset, serialize_presets
from vplay.repl import CTRL_A, CTRL_D, RAW_BANNER, RawRepl
from vplay.transport import Transport, resolve_backend
from vplay.web import make_handler, render_dashboard_html


class FakeMicroPythonTransport(Transport):
    """In-memory Transport simulating an ESP32 running MicroPython Raw REPL."""

    backend = "fake"

    def __init__(self, stdout_reply: bytes = b"HELLO FROM ESP32\r\n", stderr_reply: bytes = b"") -> None:
        self._open = False
        self.rx = bytearray()
        self.tx = bytearray()
        self.stdout_reply = stdout_reply
        self.stderr_reply = stderr_reply
        self.lines = {"dtr": False, "rts": False}
        self.baudrate = 115200

    @property
    def description(self) -> str:
        return "FakeESP32 @ 115200 baud"

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def write(self, data: bytes) -> None:
        self.tx += data
        if data.endswith(CTRL_A) and not data.endswith(b"\x05A\x01"):
            self.rx += RAW_BANNER
        elif data == b"\x05A\x01":
            # Decline raw-paste so classic Raw-REPL path is exercised cleanly.
            self.rx += b"R\x00"
        elif data.endswith(CTRL_D):
            self.rx += b"OK" + self.stdout_reply + CTRL_D + self.stderr_reply + CTRL_D + b">"

    def read(self, max_bytes: int = 4096, timeout: float = 0.05) -> bytes:
        if not self.rx:
            return b""
        out = bytes(self.rx[:max_bytes])
        del self.rx[:max_bytes]
        return out

    def set_lines(self, *, dtr: bool, rts: bool) -> None:
        self.lines = {"dtr": dtr, "rts": rts}

    def set_baudrate(self, baudrate: int) -> None:
        self.baudrate = baudrate


def test_host_detection():
    assert hostinfo.HOST in list(hostinfo.HostOS)
    assert resolve_backend("serial") == "serial"
    assert resolve_backend("usb") == "usb"
    expected_auto = "usb" if hostinfo.is_android() else "serial"
    assert resolve_backend("auto") == expected_auto


def test_config_loading(tmp_path: Path):
    toml_file = tmp_path / "vplay.toml"
    toml_file.write_text(
        "[device]\nbackend = 'serial'\nport = 'COM9'\n[pins]\nce = 4\n[web]\nport = 9090\n",
        encoding="utf-8",
    )
    cfg = load_config(toml_file)
    assert cfg.device.backend == "serial"
    assert cfg.device.port == "COM9"
    assert cfg.pins.ce == 4
    assert cfg.pins.sck == 14
    assert cfg.web.port == 9090


def test_all_payloads_are_valid_python():
    assert len(PRESET_LIST) == 18
    custom_pins = Pins(sck=18, mosi=23, miso=19, csn=5, ce=4, led=2)
    for preset in PRESET_LIST:
        assert preset.path.is_file(), f"Missing payload file for {preset.key}"
        rendered = preset.render(custom_pins)
        # Every rendered payload must compile cleanly as valid Python syntax.
        compile(rendered, str(preset.path), "exec")
        assert "PIN_CE = 4" in rendered


def test_raw_repl_execution():
    transport = FakeMicroPythonTransport(stdout_reply=b"BLINK OK\r\n")
    transport.open()
    repl = RawRepl(transport)
    streamed: list[tuple[str, str]] = []
    res = repl.exec("print('BLINK OK')", timeout=2.0, on_output=lambda t, s: streamed.append((t, s)))
    assert res.ok
    assert "BLINK OK" in res.stdout
    assert res.stderr == ""
    assert any("BLINK OK" in t for t, _ in streamed)


def test_web_control_center_endpoints(monkeypatch: pytest.MonkeyPatch):
    from http.server import ThreadingHTTPServer

    fake = FakeMicroPythonTransport(stdout_reply=b"WEB PRESET OK\n")
    fake.open()
    monkeypatch.setattr("vplay.device.open_transport", lambda _cfg: fake)

    cfg = Config()
    html = render_dashboard_html(cfg)
    for key in PRESETS:
        assert f'"{key}"' in html

    session = DeviceSession(cfg)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(session))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/diagnostics") as resp:
            diag = json.loads(resp.read().decode("utf-8"))
            assert diag["usb_detected"] is True
            assert "blink" in diag["presets_available"]

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/command?type=blink") as resp:
            cmd = json.loads(resp.read().decode("utf-8"))
            assert cmd["success"] is True
            assert "WEB PRESET OK" in cmd["output"]
    finally:
        server.shutdown()
        server.server_close()
        session.close()
