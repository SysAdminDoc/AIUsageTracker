"""Audible alarm + native Windows toast notifications.

Everything degrades gracefully: on a non-Windows box or if a backend import
fails, the calls become no-ops rather than crashing the poller.
"""
from __future__ import annotations

import math
import struct
import sys
import threading
import wave

from . import config

_IS_WINDOWS = sys.platform.startswith("win")

try:  # optional native toast backend
    from windows_toasts import Toast, WindowsToaster
    _TOASTER = WindowsToaster(config.APP_NAME)
except Exception:  # pragma: no cover
    Toast = None
    _TOASTER = None

if _IS_WINDOWS:
    import winsound
else:  # pragma: no cover
    winsound = None


def _alarm_wav_path():
    return config.data_dir() / "alarm.wav"


def _ensure_alarm_wav() -> str:
    """Synthesize a short two-tone alarm WAV once and cache it."""
    path = _alarm_wav_path()
    if path.exists():
        return str(path)
    framerate = 44100
    amplitude = 18000
    frames = bytearray()

    def tone(freq: float, ms: int):
        n = int(framerate * ms / 1000)
        for i in range(n):
            # slight fade to avoid clicks
            env = min(1.0, i / 400) * min(1.0, (n - i) / 400)
            val = int(amplitude * env * math.sin(2 * math.pi * freq * i / framerate))
            frames.extend(struct.pack("<h", val))

    def silence(ms: int):
        frames.extend(b"\x00\x00" * int(framerate * ms / 1000))

    tone(880, 180)
    silence(90)
    tone(1175, 180)
    silence(220)

    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(bytes(frames))
    return str(path)


class Alarm:
    """Controls the looping audible alarm."""

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._active

    def start(self, loop: bool = True) -> None:
        if not _IS_WINDOWS or winsound is None:
            return
        with self._lock:
            try:
                path = _ensure_alarm_wav()
                flags = winsound.SND_FILENAME | winsound.SND_ASYNC
                if loop:
                    flags |= winsound.SND_LOOP
                winsound.PlaySound(path, flags)
                self._active = True
            except Exception:
                self._active = False

    def stop(self) -> None:
        if not _IS_WINDOWS or winsound is None:
            return
        with self._lock:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._active = False


def notify(title: str, message: str) -> None:
    """Fire a native toast; fall back silently if unavailable."""
    if _TOASTER is not None and Toast is not None:
        try:
            t = Toast()
            t.text_fields = [title, message]
            _TOASTER.show_toast(t)
            return
        except Exception:
            pass
    # Fallback: plyer (cross-platform, best-effort)
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name=config.APP_NAME, timeout=10)
    except Exception:
        pass
