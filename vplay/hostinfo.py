"""Host operating-system detection and console setup.

This is the *only* module that is allowed to ask "which OS am I on?". Everything
else asks it, so platform branches stay in one place.
"""

from __future__ import annotations

import enum
import os
import sys


class HostOS(enum.Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID = "android"  # Termux (or any CPython running on Android)
    OTHER = "other"


def detect_host() -> HostOS:
    """Return the host OS.

    Android is detected first: Termux' CPython >= 3.13 reports ``sys.platform ==
    'android'``, older builds report ``'linux'`` but always export ``TERMUX_VERSION``
    / ``PREFIX=/data/data/com.termux/...``.
    """
    if sys.platform == "android" or "TERMUX_VERSION" in os.environ or os.environ.get(
        "PREFIX", ""
    ).startswith("/data/data/com.termux"):
        return HostOS.ANDROID
    if sys.platform == "win32":
        return HostOS.WINDOWS
    if sys.platform == "darwin":
        return HostOS.MACOS
    if sys.platform.startswith("linux"):
        return HostOS.LINUX
    return HostOS.OTHER


HOST = detect_host()


def is_android() -> bool:
    return HOST is HostOS.ANDROID


def is_windows() -> bool:
    return HOST is HostOS.WINDOWS


def termux_prefix() -> str | None:
    """Termux install prefix (e.g. ``/data/data/com.termux/files/usr``) or None."""
    if not is_android():
        return None
    return os.environ.get("PREFIX", "/data/data/com.termux/files/usr")


def configure_console() -> None:
    """Make stdout/stderr safe for the UTF-8 (emoji) text the device prints.

    Windows consoles may use a legacy code page (cp1252/cp437) where printing emoji
    raises ``UnicodeEncodeError``. Switching to UTF-8 with ``errors='replace'`` can
    never crash; at worst a glyph renders as ``?``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass
    if is_windows():
        try:  # Ask the console itself to render UTF-8 (Windows 10+).
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
