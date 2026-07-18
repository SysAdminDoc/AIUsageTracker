"""Configuration, paths, and persisted settings."""
from __future__ import annotations

import json
import os
import subprocess
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
THEME_KEYS = {"midnight", "graphite", "daylight"}
DEFAULT_THEME = "midnight"


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
    "alarm_sound_name": "Chime",  # which synthesized alarm to play
    "alarm_loop": True,           # repeat the sound until acknowledged
    "toast": True,
    "warn_toast_at": 90,          # toast when a window crosses this utilization
    "start_minimized": False,
    "theme": DEFAULT_THEME,
    # Per-window alarm opt-out, keyed by LimitWindow.key. Missing key => True.
    "window_alarms": {},
    # Event hooks: shell commands executed on reset/threshold. Empty = disabled.
    "on_reset_command": "",
    "on_threshold_command": "",
    # Export a JSON status file each poll for external tool integration.
    "export_status": True,
    # Webhook URL for remote alerts (Discord/Telegram). Empty = disabled.
    "webhook_url": "",
}


def window_alarm_enabled(settings: dict, key: str) -> bool:
    return bool(settings.get("window_alarms", {}).get(key, True))


def normalize_theme(value) -> str:
    """Normalize persisted theme values, including the pre-picker legacy key."""
    key = str(value or DEFAULT_THEME).strip().lower()
    if key == "mocha":
        key = DEFAULT_THEME
    return key if key in THEME_KEYS else DEFAULT_THEME


def load_settings() -> dict:
    p = settings_path()
    settings = dict(DEFAULT_SETTINGS)
    if p.exists():
        try:
            settings.update(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    settings["poll_seconds"] = max(MIN_POLL_SECONDS, int(settings.get("poll_seconds", DEFAULT_POLL_SECONDS)))
    settings["theme"] = normalize_theme(settings.get("theme"))
    return settings


def save_settings(settings: dict) -> None:
    try:
        settings_path().write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def _startup_path() -> Path:
    """Windows Startup folder shortcut path for autostart."""
    startup = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
    return startup / "AIUsageTracker.lnk"


def set_autostart(enabled: bool) -> None:
    """Create or remove a Startup folder shortcut."""
    lnk = _startup_path()
    if not enabled:
        try:
            lnk.unlink(missing_ok=True)
        except OSError:
            pass
        return
    try:
        import sys
        target = sys.executable
        if getattr(sys, "frozen", False):
            target = sys.executable
        else:
            target = str(Path(sys.executable).parent / "pythonw.exe")
        import ctypes.wintypes
        from ctypes import POINTER, byref, windll
        CoInitialize = windll.ole32.CoInitialize
        CoCreateInstance = windll.ole32.CoCreateInstance
        CoInitialize(None)

        import winreg
        lnk.parent.mkdir(parents=True, exist_ok=True)
        _write_shortcut_via_ps(str(lnk), target)
    except Exception:
        pass


def _write_shortcut_via_ps(lnk_path: str, target: str) -> None:
    """Create a .lnk shortcut using PowerShell COM (simplest reliable method)."""
    import sys
    if getattr(sys, "frozen", False):
        args = ""
    else:
        args = f'-m aiusagetracker'
    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{lnk_path}"); '
        f'$s.TargetPath = "{target}"; '
        f'$s.Arguments = "{args}"; '
        f'$s.Save()'
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, timeout=10)


def get_autostart() -> bool:
    """Check if the autostart shortcut exists."""
    return _startup_path().exists()


def run_hook(command: str, env_vars: dict[str, str]) -> None:
    """Execute a user-configured event hook command with environment context."""
    if not command or not command.strip():
        return
    try:
        env = {**os.environ, **env_vars}
        subprocess.Popen(command, shell=True, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
