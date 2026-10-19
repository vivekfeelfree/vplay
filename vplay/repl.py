"""MicroPython Raw REPL protocol, independent of the underlying transport.

Protocol summary (see micropython/tools/pyboard.py, which mpremote also uses):

1. ``\\r\\x03\\x03``      interrupt whatever is running
2. ``\\r\\x01``          enter raw REPL -> board answers ``raw REPL; CTRL-B to exit\\r\\n>``
3. send code, then ``\\x04``. Two ways:
   * *raw-paste* (MicroPython >= 1.14): ``\\x05A\\x01`` -> ``R\\x01`` + window size;
     the board sends ``\\x01`` whenever it can accept another window (flow control)
   * *classic*: write the code in small chunks; board answers ``OK``
4. board replies ``<stdout>\\x04<stderr>\\x04>``

Compared with the old host code (sleep, then read for a fixed 5 s), this knows exactly
when a script ends, separates stdout from tracebacks, streams output live, and
interrupts scripts that exceed their timeout instead of desynchronising the link.
"""

from __future__ import annotations

import codecs
import struct
import time
from dataclasses import dataclass
from typing import Callable

from vplay.transport.base import Transport, TransportError

CTRL_A, CTRL_B, CTRL_C, CTRL_D, CTRL_E = b"\x01", b"\x02", b"\x03", b"\x04", b"\x05"
RAW_BANNER = b"raw REPL; CTRL-B to exit\r\n>"

OutputCallback = Callable[[str, str], None]
"""``callback(text, stream)`` where stream is ``"stdout"`` or ``"stderr"``."""


class ReplError(TransportError):
    """The board did not follow the Raw REPL protocol."""


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return not self.timed_out and not self.stderr.strip()

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": round(self.duration, 3),
            "timed_out": self.timed_out,
        }


class _Reader:
    """Byte buffer on top of a Transport with exact/until reads and deadlines."""

    def __init__(self, transport: Transport) -> None:
        self.t = transport
        self.buf = bytearray()

    def fill(self, timeout: float) -> bool:
        chunk = self.t.read(4096, timeout=timeout)
        if chunk:
            self.buf += chunk
            return True
        return False

    def read_exact(self, n: int, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        while len(self.buf) < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self.fill(min(remaining, 0.05))
        out, self.buf = bytes(self.buf[:n]), self.buf[n:]
        return out

    def read_until(self, marker: bytes, timeout: float) -> tuple[bytes, bool]:
        """Return (data up to and including marker, found)."""
        deadline = time.monotonic() + timeout
        while True:
            idx = self.buf.find(marker)
            if idx >= 0:
                end = idx + len(marker)
                out, self.buf = bytes(self.buf[:end]), self.buf[end:]
                return out, True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                out, self.buf = bytes(self.buf), bytearray()
                return out, False
            self.fill(min(remaining, 0.05))

    def clear(self) -> None:
        self.buf.clear()


class RawRepl:
    """Execute code on a MicroPython board through its Raw REPL."""

    #: Classic-mode write pacing (same values mpremote uses).
    CHUNK_SIZE = 256
    CHUNK_DELAY = 0.01

    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self._reader = _Reader(transport)
        self._raw_paste: bool | None = None  # unknown until first exec

    # ------------------------------------------------------------ mode control

    def interrupt(self) -> None:
        """Stop any running program (Ctrl-C twice) and discard pending output."""
        self.transport.write(b"\r" + CTRL_C + CTRL_C)
        time.sleep(0.05)
        self.transport.drain(quiet_time=0.1, max_time=1.5)
        self._reader.clear()

    def enter_raw(self, attempts: int = 3) -> None:
        last = b""
        for _ in range(attempts):
            self.interrupt()
            self.transport.write(b"\r" + CTRL_A)
            data, found = self._reader.read_until(RAW_BANNER, timeout=1.5)
            if found:
                return
            last = data
        snippet = last[-120:].decode("utf-8", "replace")
        raise ReplError(
            "Board did not enter the MicroPython raw REPL. Is MicroPython flashed and the "
            f"baud rate 115200? Last bytes received: {snippet!r}"
        )

    def exit_raw(self) -> None:
        """Return to the friendly (interactive) REPL."""
        self.transport.write(b"\r" + CTRL_B)

    def soft_reset(self) -> None:
        """Soft-reboot the interpreter (clears RAM state, keeps the USB link)."""
        self.enter_raw()
        self.transport.write(CTRL_D)
        self._reader.read_until(b"soft reboot", timeout=3)
        self._reader.read_until(RAW_BANNER, timeout=3)

    # ------------------------------------------------------------- execution

    def exec(
        self,
        code: str | bytes,
        timeout: float | None = 30.0,
        on_output: OutputCallback | None = None,
    ) -> ExecResult:
        """Run ``code`` and return its output.

        ``timeout`` bounds the *script* runtime (None = no limit). On expiry the script
        is interrupted with Ctrl-C and ``ExecResult.timed_out`` is set.
        """
        payload = code.encode("utf-8") if isinstance(code, str) else code
        self.enter_raw()
        self._send_code(payload)
        return self._collect(timeout, on_output)

    def _send_code(self, payload: bytes) -> None:
        if self._raw_paste is not False:
            self.transport.write(CTRL_E + b"A" + CTRL_A)
            reply = self._reader.read_exact(2, timeout=1.0)
            if reply == b"R\x01":
                self._raw_paste = True
                self._raw_paste_write(payload)
                return
            if reply == b"R\x00":
                self._raw_paste = False
            else:
                # Firmware without raw-paste echoes the bytes back; resync and fall back.
                self._raw_paste = False
                self._reader.read_until(RAW_BANNER[-14:], timeout=1.0)
        self._classic_write(payload)

    def _raw_paste_write(self, payload: bytes) -> None:
        header = self._reader.read_exact(2, timeout=1.0)
        if len(header) != 2:
            raise ReplError("Raw-paste: missing window size")
        window = struct.unpack("<H", header)[0]
        remaining_window = window
        i = 0
        while i < len(payload):
            # Consume flow-control bytes; block only when the window is exhausted.
            while remaining_window == 0 or self._reader.buf or self._reader.fill(0):
                if not self._reader.buf and not self._reader.fill(5.0 if remaining_window == 0 else 0):
                    if remaining_window == 0:
                        raise ReplError("Raw-paste: board stopped granting flow-control window")
                    break
                byte = bytes(self._reader.buf[:1])
                del self._reader.buf[:1]
                if byte == CTRL_A:
                    remaining_window += window
                elif byte == CTRL_D:
                    self.transport.write(CTRL_D)  # board aborted (e.g. syntax error)
                    return
                else:
                    raise ReplError(f"Raw-paste: unexpected byte {byte!r}")
            chunk = payload[i : i + remaining_window]
            self.transport.write(chunk)
            remaining_window -= len(chunk)
            i += len(chunk)
        self.transport.write(CTRL_D)
        _, found = self._reader.read_until(CTRL_D, timeout=5.0)
        if not found:
            raise ReplError("Raw-paste: board did not acknowledge end of code")

    def _classic_write(self, payload: bytes) -> None:
        for i in range(0, len(payload), self.CHUNK_SIZE):
            self.transport.write(payload[i : i + self.CHUNK_SIZE])
            time.sleep(self.CHUNK_DELAY)
        self.transport.write(CTRL_D)
        reply = self._reader.read_exact(2, timeout=2.0)
        if reply != b"OK":
            raise ReplError(f"Board rejected code (expected b'OK', got {reply!r})")

    def _collect(self, timeout: float | None, on_output: OutputCallback | None) -> ExecResult:
        start = time.monotonic()
        deadline = None if timeout is None else start + timeout
        streams = {"stdout": bytearray(), "stderr": bytearray()}
        decoders = {name: codecs.getincrementaldecoder("utf-8")("replace") for name in streams}
        current = "stdout"
        timed_out = False

        def emit(name: str, data: bytes, final: bool = False) -> None:
            streams[name] += data
            if on_output is not None:
                text = decoders[name].decode(data, final)
                if text:
                    on_output(text, name)

        while True:
            reader = self._reader
            idx = reader.buf.find(CTRL_D)
            if idx >= 0:
                emit(current, bytes(reader.buf[:idx]), final=True)
                del reader.buf[: idx + 1]
                if current == "stdout":
                    current = "stderr"
                    continue
                reader.read_until(b">", timeout=1.0)
                break
            if reader.buf:
                # Keep a possible partial UTF-8 sequence for the decoder; emit the rest.
                emit(current, bytes(reader.buf))
                reader.buf.clear()
            if deadline is not None and time.monotonic() >= deadline:
                timed_out = True
                self.transport.write(CTRL_C)
                deadline = None  # give the KeyboardInterrupt traceback time to arrive
                grace_end = time.monotonic() + 3.0
                while time.monotonic() < grace_end:
                    reader.fill(0.05)
                    if reader.buf.count(CTRL_D) >= (2 if current == "stdout" else 1):
                        break
                continue
            reader.fill(0.05)

        return ExecResult(
            stdout=streams["stdout"].decode("utf-8", "replace"),
            stderr=streams["stderr"].decode("utf-8", "replace"),
            duration=time.monotonic() - start,
            timed_out=timed_out,
        )
