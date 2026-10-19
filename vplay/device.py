"""Thread-safe, auto-reconnecting device session shared by the CLI and Web server.

Provides a single point of synchronization (`threading.Lock`) and automatic
reconnection if a cable is unplugged and re-plugged between commands.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from vplay import hostinfo
from vplay.config import Config, load_config
from vplay.repl import ExecResult, OutputCallback, RawRepl
from vplay.transport import (
    DeviceBusyError,
    DeviceNotFoundError,
    Transport,
    TransportError,
    open_transport,
    resolve_backend,
)


class DeviceSession:
    """Thread-safe wrapper around Transport + RawRepl."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self._lock = threading.Lock()
        self._transport: Transport | None = None
        self._repl: RawRepl | None = None

    @property
    def is_connected(self) -> bool:
        return self._transport is not None and self._transport.is_open

    def _ensure_open_unlocked(self) -> RawRepl:
        if self._transport is None or not self._transport.is_open:
            self._transport = open_transport(self.config.device)
            self._repl = RawRepl(self._transport)
        assert self._repl is not None
        return self._repl

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self) -> None:
        if self._transport is not None:
            try:
                self._transport.close()
            finally:
                self._transport = None
                self._repl = None

    def acquire_transport(self) -> Transport:
        """Open and return the raw transport (for interactive REPL terminal)."""
        with self._lock:
            self._ensure_open_unlocked()
            assert self._transport is not None
            return self._transport

    def exec(
        self,
        code: str,
        timeout: float | None = 30.0,
        on_output: OutputCallback | None = None,
    ) -> ExecResult:
        """Execute MicroPython ``code`` on the board in a thread-safe manner.

        If the link dropped since the previous command, closes and tries once more.
        """
        with self._lock:
            for attempt in range(2):
                try:
                    repl = self._ensure_open_unlocked()
                    return repl.exec(code, timeout=timeout, on_output=on_output)
                except (DeviceNotFoundError, DeviceBusyError):
                    self._close_unlocked()
                    raise
                except TransportError:
                    self._close_unlocked()
                    if attempt == 1:
                        raise
            raise TransportError("Unreachable")

    def status(self) -> dict[str, Any]:
        """Non-destructive connection probe for `/api/diagnostics` and `vplay doctor`."""
        backend = resolve_backend(self.config.device.backend)
        info: dict[str, Any] = {
            "host_os": hostinfo.HOST.value,
            "backend": backend,
            "connected": False,
            "device": "Disconnected",
            "pins": self.config.pins.as_dict(),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if not self._lock.acquire(blocking=False):
            info["connected"] = True
            info["busy"] = True
            info["device"] = (
                self._transport.description if self._transport else "Busy (executing script)"
            )
            return info
        try:
            if self._transport is not None and self._transport.is_open:
                info["connected"] = True
                info["device"] = self._transport.description
                return info
            try:
                self._ensure_open_unlocked()
                assert self._transport is not None
                info["connected"] = True
                info["device"] = self._transport.description
            except TransportError as exc:
                info["error"] = str(exc)
        finally:
            self._lock.release()
        return info

    def __enter__(self) -> "DeviceSession":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
