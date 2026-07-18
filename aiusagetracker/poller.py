"""Background polling engine: fetch providers, detect resets, fire callbacks.

Thread-safe. The GUI (or a headless monitor) supplies callbacks and reads the
latest snapshots. Enforces a per-provider minimum poll interval so we never trip
Claude's ~180s 429 floor, while still scheduling an early wake right after a
known reset boundary to catch rollovers fast.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from . import config, storage
from .models import LimitWindow, ProviderSnapshot, ResetEvent, now_utc
from .providers import ClaudeProvider, CodexProvider
from .reset import ResetTracker

Callback = Callable[..., None]


def _build_providers(settings: dict) -> dict[str, object]:
    """Build provider instances including any extra accounts from settings."""
    providers = {"claude": ClaudeProvider(), "codex": CodexProvider()}
    for acct in settings.get("extra_accounts", []):
        ptype = acct.get("provider", "")
        path = acct.get("credential_path", "")
        aid = acct.get("name", "")
        if not path or not aid:
            continue
        if ptype == "claude":
            providers[f"claude:{aid}"] = ClaudeProvider(credential_path=path, account_id=aid)
        elif ptype == "codex":
            providers[f"codex:{aid}"] = CodexProvider(credential_path=path, account_id=aid)
    return providers


class Poller:
    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self._providers = _build_providers(settings)
        self._tracker = ResetTracker()
        self._snapshots: dict[str, ProviderSnapshot] = {}
        self._last_poll: dict[str, object] = {}
        self._warned: set[str] = set()      # window keys already warned this period
        self._health_warned: set[str] = set()  # providers warned about missing resets_at
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._primed = False

        # Callbacks (all optional, set by the host)
        self.on_snapshot: Optional[Callback] = None      # (ProviderSnapshot)
        self.on_reset: Optional[Callback] = None         # (list[ResetEvent])
        self.on_warn: Optional[Callback] = None          # (LimitWindow)
        self.on_log: Optional[Callback] = None           # (str)

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def poll_now(self) -> None:
        self._wake.set()

    # -- accessors -----------------------------------------------------------
    def snapshots(self) -> dict[str, ProviderSnapshot]:
        with self._lock:
            return dict(self._snapshots)

    def all_windows(self) -> list[LimitWindow]:
        out: list[LimitWindow] = []
        for snap in self.snapshots().values():
            if snap.ok:
                out.extend(snap.windows)
        return out

    # -- internals -----------------------------------------------------------
    def _log(self, msg: str) -> None:
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception:
                pass

    def _enabled(self, name: str) -> bool:
        return bool(self.settings.get("providers", {}).get(name, True))

    def _floor_ok(self, name: str) -> bool:
        last = self._last_poll.get(name)
        if last is None:
            return True
        return (now_utc() - last).total_seconds() >= config.MIN_POLL_SECONDS

    def _cycle(self, respect_floor: bool = False) -> None:
        collected: list[LimitWindow] = []
        for name, provider in self._providers.items():
            if not self._enabled(name):
                continue
            if respect_floor and not self._floor_ok(name):
                continue
            snap = provider.fetch()
            self._last_poll[name] = now_utc()
            with self._lock:
                self._snapshots[name] = snap
            if snap.ok:
                collected.extend(snap.windows)
                storage.cache_snapshot(name, {"windows": [w.to_dict() for w in snap.windows],
                                              "fetched_at": snap.fetched_at.isoformat(),
                                              "meta": snap.meta})
                self._log(f"{name}: ok ({len(snap.windows)} windows)")
            else:
                self._log(f"{name}: {snap.status} - {snap.error}")
            if self.on_snapshot:
                try:
                    self.on_snapshot(snap)
                except Exception:
                    pass

        if not collected:
            return

        for w in collected:
            if w.resets_at is None and w.key not in self._health_warned:
                self._health_warned.add(w.key)
                self._log(f"HEALTH: {w.provider} {w.label} missing resets_at (schema drift?)")
            elif w.resets_at is not None:
                self._health_warned.discard(w.key)

        window_data = [{"key": w.key, "provider": w.provider, "label": w.label,
                        "pct": w.utilization,
                        "resets_at": w.resets_at.isoformat() if w.resets_at else None}
                       for w in collected]
        storage.append_history([{"key": w.key, "pct": w.utilization} for w in collected])
        if self.settings.get("export_status", True):
            storage.export_status(window_data)

        # Warn on high utilization (once per period until it resets).
        for w in collected:
            warn_at = config.window_warn_threshold(self.settings, w.key)
            if w.utilization >= warn_at and w.key not in self._warned:
                self._warned.add(w.key)
                if self.on_warn:
                    try:
                        self.on_warn(w)
                    except Exception:
                        pass
                config.run_hook(self.settings.get("on_threshold_command", ""), {
                    "AIU_EVENT": "threshold",
                    "AIU_PROVIDER": w.provider,
                    "AIU_WINDOW": w.key,
                    "AIU_LABEL": w.label,
                    "AIU_UTILIZATION": f"{w.utilization:.1f}",
                })

        # Reset detection.
        if not self._primed:
            self._tracker.prime(collected)
            self._primed = True
            self._log("baseline captured")
            return

        events = self._tracker.update(collected)
        if events:
            for ev in events:
                storage.append_event(ev)
                self._warned.discard(ev.key)   # allow warning again next period
                self._log(f"RESET: {ev.provider} {ev.label}")
                config.run_hook(self.settings.get("on_reset_command", ""), {
                    "AIU_EVENT": "reset",
                    "AIU_PROVIDER": ev.provider,
                    "AIU_WINDOW": ev.key,
                    "AIU_LABEL": ev.label,
                    "AIU_UTILIZATION": f"{ev.previous_utilization or 0:.1f}",
                })
            if self.on_reset:
                try:
                    self.on_reset(events)
                except Exception:
                    pass

    def _next_wait(self) -> float:
        base = float(max(config.MIN_POLL_SECONDS, self.settings.get("poll_seconds", config.DEFAULT_POLL_SECONDS)))
        nxt = self._tracker.next_reset_at()
        if nxt is not None:
            secs = (nxt - now_utc()).total_seconds() + config.RESET_CONFIRM_DELAY
            if 0 < secs < base:
                return max(5.0, secs)
        return base

    def _run(self) -> None:
        storage.prune_history()
        # First cycle immediately.
        try:
            self._cycle(respect_floor=False)
        except Exception as e:  # never let the thread die silently
            self._log(f"cycle error: {e}")
        while not self._stop.is_set():
            wait = self._next_wait()
            triggered = self._wake.wait(timeout=wait)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                # Manual poll_now ignores the floor; scheduled wakes respect it.
                self._cycle(respect_floor=not triggered)
            except Exception as e:
                self._log(f"cycle error: {e}")
