"""Configuration, paths, and persisted settings."""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "AIUsageTracker"

# --- Credential source locations (read fresh each poll; never modified) -----
CLAUDE_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
CODEX_AUTH = Path.home() / ".codex" / "auth.json"

# --- Undocumented usage endpoints (stable as of 2026-07) --------------------
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CLAUDE_OAUTH_BETA = "oauth-2025-04-20"
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"

# User-Agent must look like the CLI or Anthropic throttles hard (429 bucket).
CLAUDE_USER_AGENT = "claude-code/2.1.170"
CODEX_USER_AGENT = "codex-cli/0.138.0"

# --- Polling ----------------------------------------------------------------
# Claude OAuth usage endpoint has a ~180s floor before aggressive 429s.
DEFAULT_POLL_SECONDS = 180
MIN_POLL_SECONDS = 180
# Extra poll fired shortly after a window's resets_at to catch the rollover fast.
RESET_CONFIRM_DELAY = 8


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_path() -> Path:
    return data_dir() / "settings.json"


def events_path() -> Path:
    return data_dir() / "reset_events.jsonl"


DEFAULT_SETTINGS = {
    "poll_seconds": DEFAULT_POLL_SECONDS,
    "providers": {"claude": True, "codex": True},
    "alarm_sound": True,
    "alarm_loop": True,           # repeat the sound until acknowledged
    "toast": True,
    "warn_toast_at": 90,          # toast when a window crosses this utilization
    "start_minimized": False,
    "theme": "mocha",
    # Per-window alarm opt-out, keyed by LimitWindow.key. Missing key => True.
    "window_alarms": {},
}


def window_alarm_enabled(settings: dict, key: str) -> bool:
    return bool(settings.get("window_alarms", {}).get(key, True))


def load_settings() -> dict:
    p = settings_path()
    settings = dict(DEFAULT_SETTINGS)
    if p.exists():
        try:
            settings.update(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    settings["poll_seconds"] = max(MIN_POLL_SECONDS, int(settings.get("poll_seconds", DEFAULT_POLL_SECONDS)))
    return settings


def save_settings(settings: dict) -> None:
    try:
        settings_path().write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass
