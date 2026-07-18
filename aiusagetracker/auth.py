"""Read OAuth tokens from the local Claude Code / Codex credential files.

Design note: Claude/Codex refresh tokens ROTATE. If this app were to refresh
them itself it could invalidate the token the CLIs are actively using and break
the user's login. So we deliberately DO NOT refresh. We read the files fresh on
every poll (the CLIs keep them current) and simply report an expired status when
a token is stale, prompting the user to run the CLI once.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config


@dataclass
class Token:
    access_token: str
    expires_at: Optional[datetime]      # aware UTC, or None if unknown

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _jwt_exp(token: str) -> Optional[datetime]:
    """Best-effort decode of a JWT 'exp' claim without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b))
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except Exception:
        return None
    return None


def read_claude_token() -> Optional[Token]:
    data = _read_json(config.CLAUDE_CREDENTIALS)
    if not data:
        return None
    oauth = data.get("claudeAiOauth") or {}
    access = oauth.get("accessToken")
    if not access:
        return None
    exp = oauth.get("expiresAt")
    expires_at = (
        datetime.fromtimestamp(int(exp) / 1000, tz=timezone.utc) if exp else None
    )
    return Token(access_token=access, expires_at=expires_at)


def read_codex_token() -> Optional[Token]:
    data = _read_json(config.CODEX_AUTH)
    if not data:
        return None
    tokens = data.get("tokens") or {}
    access = tokens.get("access_token") or data.get("access_token")
    if not access:
        return None
    return Token(access_token=access, expires_at=_jwt_exp(access))
