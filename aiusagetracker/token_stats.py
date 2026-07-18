"""Aggregate token usage from local Claude Code and Codex data files.

Claude Code: ~/.claude/projects/<slug>/<session>.jsonl — lines containing "usage"
objects with input_tokens, output_tokens, cache_creation_input_tokens, etc.

Codex: ~/.codex/logs_2.sqlite — response.completed SSE events with usage data.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TokenTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    sessions: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def formatted(self) -> str:
        t = self.total
        if t >= 1_000_000:
            return f"{t / 1_000_000:.1f}M"
        if t >= 1_000:
            return f"{t / 1_000:.0f}K"
        return str(t)


@dataclass
class UsageStats:
    claude: TokenTotals = field(default_factory=TokenTotals)
    codex: TokenTotals = field(default_factory=TokenTotals)
    scanned_at: float = 0.0

    @property
    def total(self) -> int:
        return self.claude.total + self.codex.total

    def formatted_total(self) -> str:
        t = self.total
        if t >= 1_000_000:
            return f"{t / 1_000_000:.1f}M"
        if t >= 1_000:
            return f"{t / 1_000:.0f}K"
        return str(t)


_USAGE_PATTERN = re.compile(r'"usage"\s*:\s*\{')


def _scan_claude(since_hours: float = 24.0) -> TokenTotals:
    """Sum token usage from Claude Code JSONL session logs."""
    totals = TokenTotals()
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return totals

    cutoff = time.time() - since_hours * 3600
    session_count = set()

    for jsonl_path in projects_dir.rglob("*.jsonl"):
        try:
            if jsonl_path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue

        session_id = jsonl_path.stem
        try:
            with jsonl_path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"usage"' not in line:
                        continue
                    for match in _USAGE_PATTERN.finditer(line):
                        start = match.start() + len('"usage":')
                        depth = 0
                        end = start
                        for i in range(start, min(start + 2000, len(line))):
                            if line[i] == '{':
                                depth += 1
                            elif line[i] == '}':
                                depth -= 1
                                if depth == 0:
                                    end = i + 1
                                    break
                        if end > start:
                            try:
                                usage = json.loads(line[start:end])
                                inp = usage.get("input_tokens", 0)
                                out = usage.get("output_tokens", 0)
                                if inp or out:
                                    totals.input_tokens += inp
                                    totals.output_tokens += out
                                    totals.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
                                    totals.cache_write_tokens += usage.get("cache_creation_input_tokens", 0)
                                    session_count.add(session_id)
                            except (json.JSONDecodeError, TypeError):
                                pass
        except OSError:
            continue

    totals.sessions = len(session_count)
    return totals


def _scan_codex(since_hours: float = 24.0) -> TokenTotals:
    """Sum token usage from Codex logs SQLite database."""
    totals = TokenTotals()
    db_path = Path.home() / ".codex" / "logs_2.sqlite"
    if not db_path.exists():
        return totals

    cutoff_ts = int(time.time() - since_hours * 3600)

    try:
        db = sqlite3.connect(str(db_path), timeout=5)
        db.execute("PRAGMA journal_mode=WAL")
        cur = db.cursor()
        cur.execute(
            "SELECT feedback_log_body FROM logs "
            "WHERE ts >= ? AND feedback_log_body LIKE '%response.completed%' "
            "AND feedback_log_body LIKE '%usage%'",
            (cutoff_ts,)
        )
        sessions = set()
        for (body,) in cur:
            if not body:
                continue
            if body.startswith("SSE event: "):
                body = body[len("SSE event: "):]
            try:
                data = json.loads(body)
                resp = data.get("response", {})
                usage = resp.get("usage", {})
                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                if inp or out:
                    totals.input_tokens += inp
                    totals.output_tokens += out
                    cached = usage.get("input_tokens_details", {})
                    totals.cache_read_tokens += cached.get("cached_tokens", 0)
                    totals.cache_write_tokens += cached.get("cache_write_tokens", 0)
                    resp_id = resp.get("id", "")
                    if resp_id:
                        sessions.add(resp_id[:20])
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        totals.sessions = len(sessions)
        db.close()
    except (sqlite3.Error, OSError):
        pass

    return totals


def collect(since_hours: float = 24.0) -> UsageStats:
    """Collect token usage stats from both providers."""
    return UsageStats(
        claude=_scan_claude(since_hours),
        codex=_scan_codex(since_hours),
        scanned_at=time.time(),
    )
