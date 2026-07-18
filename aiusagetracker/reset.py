"""Reset detection: compare successive snapshots and emit ResetEvents.

Primary signal is timestamp-driven: a window's `resets_at` rolling FORWARD
between two polls unambiguously means the window rolled over. We also treat a
large utilization drop as a reset when timestamps are missing.
"""
from __future__ import annotations

from typing import Optional

from .models import LimitWindow, ResetEvent, now_utc

# A resets_at must move forward by more than this to count as a genuine rollover
# (guards against sub-second jitter in the returned timestamp).
_MIN_FORWARD_SECONDS = 60
# Fallback: utilization dropping by at least this many points with no usable
# timestamp is treated as a reset.
_UTIL_DROP_POINTS = 25.0


class ResetTracker:
    """Stateful tracker; feed it snapshots, get ResetEvents back."""

    def __init__(self) -> None:
        # key -> (resets_at iso-ish datetime, utilization)
        self._prev: dict[str, tuple] = {}

    def prime(self, windows: list[LimitWindow]) -> None:
        """Seed baseline without emitting events (first run)."""
        for w in windows:
            self._prev[w.key] = (w.resets_at, w.utilization)

    def update(self, windows: list[LimitWindow]) -> list[ResetEvent]:
        events: list[ResetEvent] = []
        for w in windows:
            prev = self._prev.get(w.key)
            self._prev[w.key] = (w.resets_at, w.utilization)
            if prev is None:
                continue  # newly-seen window: baseline only
            prev_reset, prev_util = prev

            rolled = False
            if w.resets_at is not None and prev_reset is not None:
                delta = (w.resets_at - prev_reset).total_seconds()
                if delta > _MIN_FORWARD_SECONDS:
                    rolled = True
            elif w.resets_at is None or prev_reset is None:
                # No reliable timestamp on one side: fall back to util drop.
                if prev_util is not None and (prev_util - w.utilization) >= _UTIL_DROP_POINTS:
                    rolled = True

            if rolled:
                events.append(
                    ResetEvent(
                        provider=w.provider,
                        key=w.key,
                        label=w.label,
                        detected_at=now_utc(),
                        previous_reset_at=prev_reset,
                        new_reset_at=w.resets_at,
                        previous_utilization=prev_util,
                    )
                )
        return events

    def next_reset_at(self) -> Optional[object]:
        """Earliest upcoming resets_at across tracked windows (for scheduling)."""
        upcoming = [rp[0] for rp in self._prev.values() if rp[0] is not None]
        now = now_utc()
        future = [t for t in upcoming if t > now]
        return min(future) if future else None
