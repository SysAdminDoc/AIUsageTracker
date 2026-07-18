"""Provider interface + shared HTTP client."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx2 as httpx

from ..models import ProviderSnapshot

_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def parse_iso(value) -> Optional[datetime]:
    """Parse an ISO-8601 string or unix-seconds int into aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


class Provider:
    name: str = "base"

    def fetch(self) -> ProviderSnapshot:  # pragma: no cover - abstract
        raise NotImplementedError

    @staticmethod
    def _get(url: str, headers: dict) -> httpx.Response:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            return client.get(url, headers=headers)
