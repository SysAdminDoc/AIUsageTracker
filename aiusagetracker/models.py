"""Core data models shared across providers, poller, and GUI."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def severity_from_pct(pct: float) -> str:
    """Derive a severity band from a utilization percentage (0-100)."""
    if pct >= 90:
        return "critical"
    if pct >= 70:
        return "warning"
    return "normal"


@dataclass
class LimitWindow:
    """A single rate-limit window for a provider (e.g. Claude 5-hour session)."""

    provider: str                      # 'claude' | 'codex'
    key: str                           # stable identifier, e.g. 'claude:session'
    label: str                         # human label, e.g. '5-Hour Session'
    utilization: float                 # 0-100 percent used
    resets_at: Optional[datetime]      # aware UTC, or None if unknown
    severity: str = "normal"           # normal | warning | critical
    scope: Optional[str] = None        # e.g. model name for scoped windows
    window_seconds: Optional[int] = None

    def seconds_until_reset(self, ref: Optional[datetime] = None) -> Optional[float]:
        if self.resets_at is None:
            return None
        ref = ref or now_utc()
        return (self.resets_at - ref).total_seconds()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["resets_at"] = self.resets_at.isoformat() if self.resets_at else None
        return d


@dataclass
class ProviderSnapshot:
    """The result of polling one provider at a point in time."""

    provider: str
    ok: bool
    fetched_at: datetime = field(default_factory=now_utc)
    windows: list[LimitWindow] = field(default_factory=list)
    error: Optional[str] = None
    status: str = "ok"                 # ok | auth_expired | no_credentials | error
    meta: dict = field(default_factory=dict)   # plan_type, email, etc.

    def window(self, key: str) -> Optional[LimitWindow]:
        for w in self.windows:
            if w.key == key:
                return w
        return None


@dataclass
class ResetEvent:
    """Emitted when a limit window is detected to have reset."""

    provider: str
    key: str
    label: str
    detected_at: datetime
    previous_reset_at: Optional[datetime]
    new_reset_at: Optional[datetime]
    previous_utilization: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "key": self.key,
            "label": self.label,
            "detected_at": self.detected_at.isoformat(),
            "previous_reset_at": self.previous_reset_at.isoformat() if self.previous_reset_at else None,
            "new_reset_at": self.new_reset_at.isoformat() if self.new_reset_at else None,
            "previous_utilization": self.previous_utilization,
        }
