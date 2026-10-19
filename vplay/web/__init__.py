"""Local Web Control Center for vplay.

Binds to ``127.0.0.1:8080`` by default so untrusted peers on shared Wi-Fi networks
cannot execute MicroPython code on your attached hardware.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from vplay import hostinfo
from vplay.config import Config, load_config
from vplay.device import DeviceSession
from vplay.payloads import PRESETS, get_preset, serialize_presets
from vplay.transport import TransportError

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def render_dashboard_html(config: Config) -> str:
    template = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    presets_json = json.dumps(serialize_presets(config.pins))
    return template.replace("/*__PRESET_DATA__*/{}", presets_json)


def _format_exec_response(session: DeviceSession, code: str, timeout: float = 20.0) -> dict[str, Any]:
    try:
        res = session.exec(code, timeout=timeout)
    except TransportError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": f"Unexpected error: {exc}"}

    combined = res.stdout
    if res.stderr.strip():
        combined = f"{combined}\n[STDERR]\n{res.stderr}".lstrip()
    if res.timed_out:
        combined = f"{combined}\n[Timed out after {timeout:.1f}s - interrupted with Ctrl+C]".lstrip()
    return {
        "success": res.ok,
        "output": combined,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "duration": round(res.duration, 3),
        "timed_out": res.timed_out,
        **({"error": res.stderr.strip() or "Execution timed out"} if not res.ok else {}),
    }


def make_handler(session: DeviceSession):
    """Create a request handler class bound to ``session``."""

    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            # Keep server stdout concise and UTF-8 safe.
            sys_msg = fmt % args
            print(f"[web] {self.address_string()} - {sys_msg}", flush=True)

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                body = render_dashboard_html(session.config).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/command":
                qs = parse_qs(parsed.query)
                cmd_type = qs.get("type", ["blink"])[0]
                if cmd_type not in PRESETS:
                    self._send_json({"success": False, "error": f"Unknown preset: {cmd_type!r}"}, 400)
                    return
                preset = get_preset(cmd_type)
                script = preset.render(session.config.pins)
                self._send_json(_format_exec_response(session, script, timeout=preset.timeout))
                return

            if parsed.path == "/api/presets":
                self._send_json(serialize_presets(session.config.pins))
                return

            if parsed.path == "/api/diagnostics":
                st = session.status()
                self._send_json(
                    {
                        "usb_detected": st["connected"],
                        "usb_device": st["device"],
                        "host_os": st["host_os"],
                        "backend": st["backend"],
                        "pins": st["pins"],
                        "presets_available": list(PRESETS.keys()),
                        "time": st["time"],
                        **({"error": st["error"]} if "error" in st else {}),
                    }
                )
                return

            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/api/custom_eval", "/api/exec"):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                try:
                    data = json.loads(raw.decode("utf-8"))
                    code = str(data.get("code", ""))
                    timeout = float(data.get("timeout", 20.0))
                except Exception as exc:
                    self._send_json({"success": False, "error": f"Invalid JSON request: {exc}"}, 400)
                    return
                self._send_json(_format_exec_response(session, code, timeout=timeout))
                return

            self.send_response(404)
            self.end_headers()

    return DashboardHandler


def run_web_server(config: Config | None = None) -> int:
    hostinfo.configure_console()
    cfg = config or load_config()
    host = cfg.web.host
    port = cfg.web.port
    with DeviceSession(cfg) as session:
        httpd = ThreadingHTTPServer((host, port), make_handler(session))
        display_host = "localhost" if host in ("127.0.0.1", "0.0.0.0", "") else host
        print("==================================================", flush=True)
        print("🚀 vplay Web Control Center & Live Code Inspector", flush=True)
        print(f"   Host OS : {hostinfo.HOST.value}", flush=True)
        print(f"   URL     : http://{display_host}:{port}", flush=True)
        print("==================================================", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down web server...", flush=True)
        finally:
            httpd.server_close()
    return 0
