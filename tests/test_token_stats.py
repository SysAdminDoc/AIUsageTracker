"""Tests for token_stats module."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from aiusagetracker.token_stats import TokenTotals, _scan_claude, _scan_codex


def test_token_totals_formatted():
    t = TokenTotals(input_tokens=500_000, output_tokens=500_000)
    assert t.total == 1_000_000
    assert t.formatted() == "1.0M"

    t2 = TokenTotals(input_tokens=50_000, output_tokens=5_000)
    assert t2.formatted() == "55K"

    t3 = TokenTotals(input_tokens=100, output_tokens=50)
    assert t3.formatted() == "150"


def test_scan_claude_parses_usage_from_jsonl(tmp_path):
    projects = tmp_path / "projects" / "slug"
    projects.mkdir(parents=True)
    session_file = projects / "abc123.jsonl"
    line = json.dumps({
        "type": "assistant",
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 200,
            "cache_read_input_tokens": 500,
            "cache_creation_input_tokens": 300,
        }
    })
    session_file.write_text(line + "\n" + line + "\n", encoding="utf-8")

    with patch("aiusagetracker.token_stats.Path.home", return_value=tmp_path / "fake"):
        (tmp_path / "fake" / ".claude" / "projects").mkdir(parents=True)
    with patch("pathlib.Path.home", return_value=tmp_path):
        (tmp_path / ".claude" / "projects").mkdir(parents=True)
        dest = tmp_path / ".claude" / "projects" / "slug" / "abc123.jsonl"
        dest.parent.mkdir(parents=True)
        dest.write_text(line + "\n" + line + "\n", encoding="utf-8")
        totals = _scan_claude(since_hours=999)

    assert totals.input_tokens == 2000
    assert totals.output_tokens == 400
    assert totals.cache_read_tokens == 1000
    assert totals.cache_write_tokens == 600
    assert totals.sessions == 1
