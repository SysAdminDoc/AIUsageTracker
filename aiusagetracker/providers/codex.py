"""Codex (ChatGPT Codex cloud) usage provider.

Reads the backend endpoint behind chatgpt.com/codex/.../analytics:
    GET https://chatgpt.com/backend-api/wham/usage
"""
from __future__ import annotations

from .. import config
from ..auth import read_codex_token
from ..models import LimitWindow, ProviderSnapshot, now_utc, severity_from_pct
from .base import Provider, parse_iso


def _window_label(window_seconds) -> str:
    try:
        secs = int(window_seconds or 0)
    except (TypeError, ValueError):
        secs = 0
    if secs and secs <= 5 * 3600 + 600:
        return "5-Hour"
    if secs and secs <= 24 * 3600 + 600:
        return "Daily"
    if secs:
        return "Weekly"
    return "Window"


def _window_to_limit(rl_window: dict, name: str, key: str) -> LimitWindow | None:
    if not isinstance(rl_window, dict):
        return None
    pct = float(rl_window.get("used_percent", 0) or 0)
    return LimitWindow(
        provider="codex",
        key=key,
        label=name,
        utilization=pct,
        resets_at=parse_iso(rl_window.get("reset_at")),
        severity=severity_from_pct(pct),
        window_seconds=rl_window.get("limit_window_seconds"),
    )


def parse_codex_usage(data: dict, provider_name: str = "codex") -> list[LimitWindow]:
    """Pure parser: turn the wham/usage JSON into LimitWindow objects."""
    windows: list[LimitWindow] = []
    rl = data.get("rate_limit") or {}

    for slot, base_key in (("primary_window", "primary"), ("secondary_window", "secondary")):
        w = rl.get(slot)
        if isinstance(w, dict):
            label = _window_label(w.get("limit_window_seconds"))
            lw = _window_to_limit(w, label, f"{provider_name}:{base_key}")
            if lw:
                lw.provider = provider_name
                windows.append(lw)

    # Per-feature extra limits (e.g. a specific model's weekly cap).
    for extra in data.get("additional_rate_limits") or []:
        if not isinstance(extra, dict):
            continue
        feat = extra.get("limit_name") or extra.get("metered_feature") or "feature"
        inner = (extra.get("rate_limit") or {}).get("primary_window")
        if isinstance(inner, dict):
            label = f"{feat} ({_window_label(inner.get('limit_window_seconds'))})"
            lw = _window_to_limit(inner, label, f"{provider_name}:extra:{feat}")
            if lw:
                lw.provider = provider_name
                lw.scope = feat
                windows.append(lw)
    return windows


class CodexProvider(Provider):
    name = "codex"

    def __init__(self, credential_path=None, account_id=None):
        self._credential_path = credential_path
        if account_id:
            self.name = f"codex:{account_id}"

    def fetch(self) -> ProviderSnapshot:
        if self._credential_path:
            from pathlib import Path
            from ..auth import _read_json, Token, _jwt_exp
            data = _read_json(Path(self._credential_path))
            if not data:
                return ProviderSnapshot(
                    provider=self.name, ok=False, status="no_credentials",
                    error=f"Cannot read {self._credential_path}")
            tokens = data.get("tokens") or {}
            access = tokens.get("access_token") or data.get("access_token")
            if not access:
                return ProviderSnapshot(
                    provider=self.name, ok=False, status="no_credentials",
                    error="No access_token in credentials file")
            token = Token(access_token=access, expires_at=_jwt_exp(access))
        else:
            token = read_codex_token()
        if token is None:
            return ProviderSnapshot(
                provider=self.name, ok=False, status="no_credentials",
                error="No Codex credentials found. Run `codex` and log in.",
            )
        if token.expired:
            return ProviderSnapshot(
                provider=self.name, ok=False, status="auth_expired",
                error="Codex login token expired. Run `codex` to refresh it.",
            )
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "User-Agent": config.CODEX_USER_AGENT,
            "Accept": "application/json",
        }
        try:
            resp = self._get(config.CODEX_USAGE_URL, headers)
        except Exception as e:
            return ProviderSnapshot(provider=self.name, ok=False, status="error",
                                    error=f"Request failed: {e}")

        if resp.status_code == 401:
            return ProviderSnapshot(provider=self.name, ok=False, status="auth_expired",
                                    error="Codex token rejected (401). Run `codex` to refresh.")
        if resp.status_code != 200:
            return ProviderSnapshot(provider=self.name, ok=False, status="error",
                                    error=f"HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            return ProviderSnapshot(provider=self.name, ok=False, status="error",
                                    error="Non-JSON response")

        windows = parse_codex_usage(data, self.name)
        meta = {
            "plan_type": data.get("plan_type"),
            "email": data.get("email"),
        }
        return ProviderSnapshot(provider=self.name, ok=True, fetched_at=now_utc(),
                                windows=windows, meta=meta)
