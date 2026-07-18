"""Persist reset events, snapshots, and usage history to the app data dir."""
from __future__ import annotations

import json
import time
from typing import Optional

from . import config
from .models import ResetEvent


def append_event(event: ResetEvent) -> None:
    try:
        with config.events_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
    except OSError:
        pass


def load_events(limit: int = 200) -> list[dict]:
    p = config.events_path()
    if not p.exists():
        return []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def cache_snapshot(provider: str, payload: dict) -> None:
    try:
        (config.data_dir() / f"snapshot_{provider}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def load_cached_snapshot(provider: str) -> Optional[dict]:
    p = config.data_dir() / f"snapshot_{provider}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# --- Usage history (time-series) -------------------------------------------
HISTORY_MAX_AGE_DAYS = 30


def _history_path():
    return config.data_dir() / "usage_history.jsonl"


def append_history(windows: list[dict]) -> None:
    """Append a timestamped usage record for all active windows."""
    if not windows:
        return
    record = {"ts": time.time(), "windows": windows}
    try:
        with _history_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def load_history(since_hours: float = 24.0) -> list[dict]:
    """Load usage history records from the last N hours."""
    p = _history_path()
    if not p.exists():
        return []
    cutoff = time.time() - since_hours * 3600
    out = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("ts", 0) >= cutoff:
                        out.append(rec)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return out


def export_status(windows: list[dict]) -> None:
    """Write current_status.json for external tools (agents, scripts) to read."""
    payload = {"ts": time.time(), "windows": windows}
    try:
        (config.data_dir() / "current_status.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def prune_history() -> None:
    """Remove records older than HISTORY_MAX_AGE_DAYS. Called periodically."""
    p = _history_path()
    if not p.exists():
        return
    cutoff = time.time() - HISTORY_MAX_AGE_DAYS * 86400
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    kept = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("ts", 0) >= cutoff:
                kept.append(line)
        except json.JSONDecodeError:
            continue
    try:
        p.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    except OSError:
        pass
