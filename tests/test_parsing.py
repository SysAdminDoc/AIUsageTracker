"""Parser tests using the real endpoint response shapes."""
from datetime import timezone

from aiusagetracker.providers.claude import parse_claude_usage
from aiusagetracker.providers.codex import parse_codex_usage

CLAUDE_SAMPLE = {
    "five_hour": {"utilization": 37.0, "resets_at": "2026-07-18T02:29:59.735011+00:00"},
    "seven_day": {"utilization": 71.0, "resets_at": "2026-07-21T16:59:59.735044+00:00"},
    "limits": [
        {"kind": "session", "group": "session", "percent": 37, "severity": "normal",
         "resets_at": "2026-07-18T02:29:59.735011+00:00", "scope": None, "is_active": False},
        {"kind": "weekly_all", "group": "weekly", "percent": 71, "severity": "normal",
         "resets_at": "2026-07-21T16:59:59.735044+00:00", "scope": None, "is_active": False},
        {"kind": "weekly_scoped", "group": "weekly", "percent": 91, "severity": "critical",
         "resets_at": "2026-07-21T16:59:59.735536+00:00",
         "scope": {"model": {"id": None, "display_name": "Fable"}, "surface": None}, "is_active": True},
    ],
}

CODEX_SAMPLE = {
    "plan_type": "pro",
    "email": "x@example.com",
    "rate_limit": {
        "allowed": True,
        "primary_window": {"used_percent": 94, "limit_window_seconds": 604800,
                           "reset_after_seconds": 448654, "reset_at": 1784783247},
        "secondary_window": None,
    },
    "additional_rate_limits": [
        {"limit_name": "GPT-5.3-Codex-Spark", "metered_feature": "codex_bengalfox",
         "rate_limit": {"primary_window": {"used_percent": 0, "limit_window_seconds": 604800,
                                           "reset_at": 1784939394}}},
    ],
}


def test_claude_uses_limits_array():
    windows = parse_claude_usage(CLAUDE_SAMPLE)
    keys = {w.key for w in windows}
    assert "claude:session" in keys
    assert "claude:weekly_all" in keys
    scoped = next(w for w in windows if w.scope == "Fable")
    assert scoped.utilization == 91
    assert scoped.severity == "critical"
    assert scoped.resets_at.tzinfo == timezone.utc


def test_claude_fallback_top_level():
    data = {"five_hour": CLAUDE_SAMPLE["five_hour"], "seven_day": CLAUDE_SAMPLE["seven_day"]}
    windows = parse_claude_usage(data)
    assert len(windows) == 2
    assert windows[0].utilization == 37.0


def test_codex_primary_and_extra():
    windows = parse_codex_usage(CODEX_SAMPLE)
    keys = {w.key for w in windows}
    assert "codex:primary" in keys
    primary = next(w for w in windows if w.key == "codex:primary")
    assert primary.utilization == 94
    assert primary.label == "Weekly"           # 604800s -> Weekly
    assert primary.severity == "critical"       # 94% -> critical
    assert primary.resets_at.tzinfo == timezone.utc
    extra = next(w for w in windows if w.key.startswith("codex:extra:"))
    assert "GPT-5.3-Codex-Spark" in extra.label


def test_codex_five_hour_label():
    data = {"rate_limit": {"primary_window": {"used_percent": 10, "limit_window_seconds": 18000,
                                              "reset_at": 1784783247}}}
    windows = parse_codex_usage(data)
    assert windows[0].label == "5-Hour"
    assert windows[0].severity == "normal"
