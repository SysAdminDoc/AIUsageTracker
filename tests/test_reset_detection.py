"""Reset-detection tests."""
from datetime import timedelta

from aiusagetracker.models import LimitWindow, now_utc
from aiusagetracker.reset import ResetTracker


def _win(key, util, reset_at):
    return LimitWindow(provider="claude", key=key, label=key, utilization=util, resets_at=reset_at)


def test_no_event_on_prime():
    t = ResetTracker()
    r = now_utc() + timedelta(hours=5)
    t.prime([_win("claude:session", 50, r)])
    events = t.update([_win("claude:session", 55, r)])
    assert events == []


def test_reset_when_resets_at_rolls_forward():
    t = ResetTracker()
    r1 = now_utc() + timedelta(minutes=2)
    t.prime([_win("claude:session", 88, r1)])
    r2 = r1 + timedelta(hours=5)          # window rolled to a new period
    events = t.update([_win("claude:session", 3, r2)])
    assert len(events) == 1
    ev = events[0]
    assert ev.key == "claude:session"
    assert ev.previous_reset_at == r1
    assert ev.new_reset_at == r2


def test_no_reset_on_minor_jitter():
    t = ResetTracker()
    r1 = now_utc() + timedelta(hours=1)
    t.prime([_win("claude:session", 50, r1)])
    r2 = r1 + timedelta(seconds=5)        # sub-threshold jitter
    events = t.update([_win("claude:session", 51, r2)])
    assert events == []


def test_util_drop_fallback_without_timestamp():
    t = ResetTracker()
    t.prime([_win("codex:primary", 95, None)])
    events = t.update([_win("codex:primary", 2, None)])
    assert len(events) == 1


def test_next_reset_at_returns_earliest_future():
    t = ResetTracker()
    near = now_utc() + timedelta(minutes=10)
    far = now_utc() + timedelta(hours=8)
    past = now_utc() - timedelta(hours=1)
    t.prime([_win("a", 1, far), _win("b", 1, near), _win("c", 1, past)])
    assert t.next_reset_at() == near
