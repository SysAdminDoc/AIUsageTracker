"""In-memory example data. No credentials, network, disk storage or notifications."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

from .config import DEFAULT_SETTINGS
from .models import LimitWindow, ProviderSnapshot, now_utc, severity_from_pct
from .token_stats import TokenTotals, UsageStats


class SilentAlarm:
    active = False

    def start(self, *args, **kwargs):
        pass

    def stop(self):
        pass


class DemoSession:
    def __init__(self, theme="midnight"):
        self.settings = deepcopy(DEFAULT_SETTINGS)
        self.settings.update(theme=theme, alarm_sound=False, toast=False, export_status=False)
        self.on_snapshot = self.on_reset = self.on_warn = self.on_log = None
        self._snapshots = {}
        now = now_utc()
        windows = {
            "claude": [("session", "5-Hour Session", 68, 104),
                       ("weekly", "Weekly Usage", 42, 3860)],
            "codex": [("session", "5-Hour Session", 23, 192),
                      ("weekly", "Weekly Usage", 57, 5300)],
        }
        for provider, rows in windows.items():
            self._snapshots[provider] = ProviderSnapshot(
                provider, True, fetched_at=now, meta={"plan_type": "Example"},
                windows=[LimitWindow(provider, f"{provider}:{key}", label, pct,
                                     now + timedelta(minutes=minutes), severity_from_pct(pct))
                         for key, label, pct, minutes in rows],
            )
        self.events = [
            {"provider": provider, "label": "5-Hour Session",
             "key": f"{provider}:session", "detected_at": (now - timedelta(hours=hours)).isoformat()}
            for provider, hours in [("claude", 28), ("codex", 23), ("claude", 8), ("codex", 3)]
        ]
        self.history = [
            {"ts": (now - timedelta(days=day)).timestamp(),
             "windows": [{"key": "claude:session", "pct": (day * 17 + 23) % 100},
                         {"key": "codex:session", "pct": (day * 11 + 41) % 100}]}
            for day in range(28)
        ]
        self.stats = UsageStats(TokenTotals(162000, 32000, sessions=6),
                                TokenTotals(91000, 21000, sessions=4))

    def snapshots(self):
        return dict(self._snapshots)

    def start(self):
        self.poll_now()

    def poll_now(self):
        for snapshot in self._snapshots.values():
            if self.on_snapshot:
                self.on_snapshot(snapshot)

    def stop(self):
        pass
