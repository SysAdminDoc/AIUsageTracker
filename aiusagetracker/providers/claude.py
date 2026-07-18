"""Claude (claude.ai / Claude Code) usage provider.

Reads the OAuth usage endpoint that powers claude.ai/settings/usage:
    GET https://api.anthropic.com/api/oauth/usage
"""
from __future__ import annotations

from .. import config
from ..auth import read_claude_token
from ..models import LimitWindow, ProviderSnapshot, now_utc, severity_from_pct
from .base import Provider, parse_iso

# kind -> (label, sort priority)
_KIND_LABELS = {
    "session": ("5-Hour Session", 0),
    "weekly_all": ("Weekly (All Models)", 1),
    "weekly_scoped": ("Weekly", 2),
}


def parse_claude_usage(data: dict) -> list[LimitWindow]:
    """Pure parser: turn the usage JSON into LimitWindow objects."""
    windows: list[LimitWindow] = []

    # Preferred: the rich `limits[]` array (session / weekly_all / weekly_scoped).
    limits = data.get("limits")
    if isinstance(limits, list) and limits:
        for item in limits:
            kind = item.get("kind", "")
            base_label, _ = _KIND_LABELS.get(kind, (kind.replace("_", " ").title(), 9))
            scope_model = None
            scope = item.get("scope") or {}
            model = (scope or {}).get("model") or {}
            scope_model = model.get("display_name")
            label = base_label
            key = f"claude:{kind}"
            if scope_model:
                label = f"{base_label} - {scope_model}"
                key = f"claude:{kind}:{scope_model}"
            pct = float(item.get("percent", 0) or 0)
            windows.append(
                LimitWindow(
                    provider="claude",
                    key=key,
                    label=label,
                    utilization=pct,
                    resets_at=parse_iso(item.get("resets_at")),
                    severity=item.get("severity") or severity_from_pct(pct),
                    scope=scope_model,
                )
            )
        return windows

    # Fallback: top-level five_hour / seven_day objects.
    mapping = [
        ("five_hour", "5-Hour Session", "claude:session"),
        ("seven_day", "Weekly (All Models)", "claude:weekly_all"),
        ("seven_day_opus", "Weekly (Opus)", "claude:weekly_opus"),
        ("seven_day_sonnet", "Weekly (Sonnet)", "claude:weekly_sonnet"),
    ]
    for field_name, label, key in mapping:
        obj = data.get(field_name)
        if not isinstance(obj, dict):
            continue
        pct = float(obj.get("utilization", 0) or 0)
        windows.append(
            LimitWindow(
                provider="claude",
                key=key,
                label=label,
                utilization=pct,
                resets_at=parse_iso(obj.get("resets_at")),
                severity=severity_from_pct(pct),
            )
        )
    return windows


class ClaudeProvider(Provider):
    name = "claude"

    def fetch(self) -> ProviderSnapshot:
        token = read_claude_token()
        if token is None:
            return ProviderSnapshot(
                provider="claude", ok=False, status="no_credentials",
                error="No Claude credentials found (~/.claude/.credentials.json). "
                      "Run `claude` and log in.",
            )
        if token.expired:
            return ProviderSnapshot(
                provider="claude", ok=False, status="auth_expired",
                error="Claude login token expired. Open Claude Code to refresh it.",
            )
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "anthropic-beta": config.CLAUDE_OAUTH_BETA,
            "User-Agent": config.CLAUDE_USER_AGENT,
            "Accept": "application/json",
        }
        try:
            resp = self._get(config.CLAUDE_USAGE_URL, headers)
        except Exception as e:  # network / DNS / TLS
            return ProviderSnapshot(provider="claude", ok=False, status="error",
                                    error=f"Request failed: {e}")

        if resp.status_code == 401:
            return ProviderSnapshot(provider="claude", ok=False, status="auth_expired",
                                    error="Claude token rejected (401). Open Claude Code to refresh.")
        if resp.status_code == 429:
            return ProviderSnapshot(provider="claude", ok=False, status="error",
                                    error="Rate limited (429) - polling too fast; backing off.")
        if resp.status_code != 200:
            return ProviderSnapshot(provider="claude", ok=False, status="error",
                                    error=f"HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            return ProviderSnapshot(provider="claude", ok=False, status="error",
                                    error="Non-JSON response")

        windows = parse_claude_usage(data)
        meta = {"subscription": data.get("subscriptionType")}
        return ProviderSnapshot(provider="claude", ok=True, fetched_at=now_utc(),
                                windows=windows, meta=meta)
