"""Audible alarm (multiple selectable sounds) + native Windows toasts + webhook.

Sounds are synthesized once and cached as loopable WAVs in the app data dir, so
there are no binary audio assets to ship. Everything degrades gracefully: on a
non-Windows box or if a backend import fails, calls become no-ops.
"""
from __future__ import annotations

import json
import math
import struct
import sys
import threading
import wave

from . import config

_IS_WINDOWS = sys.platform.startswith("win")
_RATE = 44100

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


# --- synthesis helpers ------------------------------------------------------
def _partials(freq, ms, partials=((1, 1.0),), attack=0.01, release=0.2, decay=0.0):
    """Render one tone as a list of float samples in [-1, 1]."""
    n = int(_RATE * ms / 1000)
    out = [0.0] * n
    atk = max(1, int(_RATE * attack))
    rel = max(1, int(_RATE * release))
    for i in range(n):
        env = min(1.0, i / atk) * min(1.0, (n - i) / rel)
        if decay:
            env *= math.exp(-decay * i / _RATE)
        s = 0.0
        for mult, amp in partials:
            s += amp * math.sin(2 * math.pi * freq * mult * i / _RATE)
        out[i] = env * s
    return out


def _silence(ms):
    return [0.0] * int(_RATE * ms / 1000)


def _sweep(f0, f1, ms, amp=0.9):
    n = int(_RATE * ms / 1000)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / n)
        phase += 2 * math.pi * f / _RATE
        env = min(1.0, i / 400) * min(1.0, (n - i) / 400)
        out[i] = amp * env * math.sin(phase)
    return out


def _bell(freq, ms):
    return _partials(freq, ms, partials=((1, 1.0), (2.01, 0.5), (2.99, 0.28), (4.2, 0.12)),
                     attack=0.002, release=0.02, decay=4.5)


def _chime(freq, ms):
    return _partials(freq, ms, partials=((1, 1.0), (2, 0.25), (3, 0.08)),
                     attack=0.01, release=0.25)


# --- sound library ----------------------------------------------------------
def _s_chime():
    seq = []
    for f in (659.25, 830.61, 987.77):        # E5, G#5, B5 - pleasant rising
        seq += _chime(f, 260)
    return seq + _silence(500)


def _s_alert():
    seq = []
    for _ in range(2):
        seq += _partials(880, 170, ((1, 0.9), (2, 0.2))) + _silence(70)
        seq += _partials(1174.66, 170, ((1, 0.9), (2, 0.2))) + _silence(220)
    return seq + _silence(300)


def _s_pulse():
    seq = []
    for _ in range(4):
        seq += _partials(1046.5, 90, ((1, 0.8), (2, 0.3)), attack=0.005, release=0.04) + _silence(80)
    return seq + _silence(500)


def _s_bell():
    return _bell(1318.5, 900) + _silence(350)


def _s_siren():
    return _sweep(600, 1200, 500) + _sweep(1200, 600, 500) + _silence(200)


def _s_arcade():
    seq = []
    for f in (523.25, 659.25, 783.99, 1046.5):   # C5 E5 G5 C6 blip run
        seq += _partials(f, 80, ((1, 0.7), (2, 0.4), (3, 0.2)), attack=0.003, release=0.03)
    return seq + _silence(450)


SOUNDS = {
    "Chime": _s_chime,
    "Alert": _s_alert,
    "Pulse": _s_pulse,
    "Bell": _s_bell,
    "Siren": _s_siren,
    "Arcade": _s_arcade,
}
SOUND_NAMES = list(SOUNDS.keys())
DEFAULT_SOUND = "Chime"


def _write_wav(path, samples):
    amp = 26000
    frames = bytearray()
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * amp)
        frames += struct.pack("<h", v)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(bytes(frames))


def ensure_wav(name: str) -> str:
    name = name if name in SOUNDS else DEFAULT_SOUND
    path = config.data_dir() / f"alarm_{name.lower()}.wav"
    if not path.exists():
        _write_wav(path, SOUNDS[name]())
    return str(path)


# --- alarm control ----------------------------------------------------------
class Alarm:
    def __init__(self) -> None:
        self._active = False
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._active

    def start(self, loop: bool = True, sound: str = DEFAULT_SOUND) -> None:
        if not _IS_WINDOWS or winsound is None:
            return
        with self._lock:
            try:
                path = ensure_wav(sound)
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


def preview(sound: str) -> None:
    """Play a sound once (non-looping) for the settings 'Test' button."""
    if not _IS_WINDOWS or winsound is None:
        return
    try:
        path = ensure_wav(sound)
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


def notify(title: str, message: str) -> None:
    if _TOASTER is not None and Toast is not None:
        try:
            t = Toast()
            t.text_fields = [title, message]
            _TOASTER.show_toast(t)
        except Exception:
            pass


def send_webhook(url: str, title: str, message: str) -> None:
    """POST a reset/threshold alert to a Discord or Telegram webhook."""
    if not url or not url.strip():
        return
    threading.Thread(target=_webhook_post, args=(url.strip(), title, message),
                     daemon=True).start()


def _webhook_post(url: str, title: str, message: str) -> None:
    try:
        import httpx2 as httpx
        if "discord" in url.lower():
            payload = {"content": f"**{title}**\n{message}"}
        elif "telegram" in url.lower():
            payload = {"text": f"*{title}*\n{message}", "parse_mode": "Markdown"}
        else:
            payload = {"title": title, "message": message}
        with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
            client.post(url, json=payload)
    except Exception:
        pass
