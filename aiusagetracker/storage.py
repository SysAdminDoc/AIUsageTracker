"""Persist reset events and the latest snapshot to the app data dir."""
from __future__ import annotations

import json
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
