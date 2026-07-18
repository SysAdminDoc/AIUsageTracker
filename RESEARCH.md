# Research — AIUsageTracker

Date: 2026-07-18 — replaces all prior research.

## Executive Summary

AIUsageTracker is a focused Windows desktop alarm tool that monitors Claude and Codex usage via local OAuth tokens and fires reset notifications. At v0.2.0, its core value prop — dual-provider reset alarms with per-bar toggles — is unique in the ecosystem. No single competitor covers both providers + sound alarms + Windows tray + no-token-refresh safety. The highest-value direction is deepening the alarm/prediction UX (progressive threshold alerts, burn-rate forecasting, dynamic tray icon) while hardening the dependency stack (7 Pillow CVEs, abandoned httpx upstream).

**Top opportunities (priority order):**
1. Upgrade Pillow to >= 12.3.0 (7 CVEs in 2026, including buffer overflows)
2. Migrate httpx → httpx2 (Pydantic fork; original abandoned Feb 2026)
3. Dynamic tray icon showing highest-usage % or color-coded severity
4. Burn-rate / ETA-to-exhaustion forecast ("you'll hit the wall in 47 min")
5. Event hooks — run shell commands on reset/threshold (competitor parity)
6. Remove plyer (stale, windows-toasts already covers all notification needs)
7. Usage sparklines in LimitRow cards (trend, not just point-in-time)
8. Historical usage persistence (enable trends, heatmaps, forecasting)
9. PyInstaller exe size reduction (45MB → ~20MB with clean venv + UPX + excludes)
10. Multiple account/credential support (power users running 2+ subscriptions)

## Product Map

**Core workflows:**
- Poll Claude/Codex usage endpoints every 180s via background thread
- Detect usage-window resets (timestamp rollover or utilization drop)
- Fire audible alarm + toast + banner on reset; per-bar toggle controls
- Display real-time utilization bars with countdown to next reset
- Persist reset events to JSONL for activity feed

**User personas:**
- Power developer using Claude Code + Codex CLI daily, AFK between sessions, wants to resume immediately when limits reset
- Multi-tool developer switching providers mid-day when one limit is hit, needs at-a-glance comparison

**Platforms:** Windows 10/11 (single-file exe + system tray)

**Key integrations:** `~/.claude/.credentials.json` (read-only), `~/.codex/auth.json` (read-only), `api.anthropic.com/api/oauth/usage`, `chatgpt.com/backend-api/wham/usage`

## Competitive Landscape

### jens-duttke/usage-monitor-for-claude (~150 stars)
Windows tray, single EXE (~2MB), TypeScript. Zero-config, dynamic quota detection, configurable threshold alerts, event commands (shell hooks on reset/threshold), start-with-Windows.
- **Learn from:** Event hooks (shell command on reset), extreme binary size efficiency, threshold-based alerts
- **Avoid:** Claude-only scope; no multi-provider value

### steipete/CodexBar (~7,000 stars)
macOS menu bar (Swift), 63 providers, inline spend charts, CLI for Linux.
- **Learn from:** Provider plugin architecture, inline sparkline charts, CLI mode for scripting
- **Avoid:** macOS ecosystem lock-in; feature surface bloat competing with 63 providers

### Javis603/token-monitor (~200 stars)
Desktop widget (Electron), Windows + macOS, multi-device LAN sync, Discord Rich Presence.
- **Learn from:** Multi-device sync concept, broad tool support (10+), iOS widget integration
- **Avoid:** Electron weight, complexity of LAN hub protocol

### mm7894215/TokenTracker (~980 stars)
Desktop app (macOS + Windows), 27 tools, desktop pet, achievements/gamification.
- **Learn from:** Widget variety (4 types), gamification as engagement driver
- **Avoid:** Novelty features (desktop pet) that dilute focus; gamification may not suit a developer-tools audience

### Maciek-roboblog/Claude-Code-Usage-Monitor (~8,400 stars)
Python CLI/TUI (Rich), realtime/daily/monthly views, burn rate analytics, P90 calculator, session forecasting, 700+ tests.
- **Learn from:** Burn-rate calculation, session forecasting, comprehensive test suite
- **Avoid:** CLI-only (no GUI/tray), no alarm/notification system

### bozdemir/claude-usage-widget
Cross-platform Python/PySide6, 11 themes, burn/spike alerts, AI-generated weekly reports, monthly spend cap.
- **Learn from:** Burn-rate spike alerts, spend cap concept, theme variety
- **Avoid:** Qt dependency size, AI-generated reports (unnecessary complexity)

### projectvelox/claude-usage-widget
Windows always-on-top floating widget, 7-day history graph, reset hooks.
- **Learn from:** 7-day history graph visualization, hook system
- **Avoid:** 88MB binary size; Claude-only

## Security, Privacy, and Reliability

**Active vulnerabilities:**
- `Pillow < 12.3.0`: CVE-2026-25990 (High, buffer overflow via PSD), CVE-2026-42308 (Medium, integer overflow in font glyph), CVE-2026-42309 (High, heap buffer overflow from nested coords), CVE-2026-54059/54060 (Medium, decompression bombs), CVE-2026-55379/55380 (Medium, excessive memory DoS). **Fix: pin `Pillow>=12.3.0`.**
- `httpx`: Encode maintainer closed all community channels Feb 2026; no releases since Dec 2024 v0.28.1. No future security patches. **Fix: migrate to `httpx2` (Pydantic fork, identical API).**
- `plyer`: No PyPI release in 12+ months; `windows-toasts` already handles all notification needs. **Fix: remove entirely.**

**Missing guardrails:**
- No file-permission check on token files (warn if world-readable)
- No graceful handling when token JSON is malformed/truncated (partial write during CLI rotation)
- No rate-limit backoff beyond the 180s floor (if 429s persist, should exponential-backoff)

**Recovery needs:**
- If both tokens expire simultaneously, the app shows "auth_expired" but provides no guidance on how to re-authenticate
- No export/import of settings.json (portability between machines)

## Architecture Assessment

**Module boundaries (good):**
- Clean provider abstraction via `providers/base.py`
- Config/storage/auth properly separated
- GUI event marshalling via queue pattern is correct

**Refactor candidates:**
- `gui/app.py` (~900 LoC): App class handles layout, widgets, event handling, and settings dialog. Extract `SettingsDialog` and widget classes into separate files.
- `alarm.py` (~208 LoC): WAV synthesis is a self-contained concern; alarm orchestration (start/stop/preview) is another. Could split but not urgent.
- `config.py`: Mixes endpoint constants, settings I/O, and theme config. Settings persistence could become its own module if features grow.

**Test gaps:**
- No GUI tests (smoke test, widget creation, event marshalling)
- No integration test for actual HTTP polling (mock httpx transport)
- No test for alarm.py WAV synthesis or playback
- No test for storage.py JSONL append/read
- 13 tests total — solid for core logic but thin for a shipped product

## Rejected Ideas

| Idea | Reason | Source |
|------|--------|--------|
| Gamification / achievements / desktop pet | Misaligned with developer-tool UX; novelty over utility | TokenTracker |
| Global leaderboard / social features | Privacy-hostile; usage data is sensitive | tokscale |
| Enterprise observability (traces, evals, prompt mgmt) | Overkill; this is a personal subscription monitor, not an LLM ops platform | Langfuse, Helicone, Portkey |
| Browser extension for claude.ai DOM scraping | Fragile, breaks on redesigns, auth complexity | lugia19/Claude-Usage-Extension |
| macOS/Linux port | Stack is deeply Windows (winsound, windows-toasts, APPDATA, tray). Cross-platform would require rewrite | Multiple requests |
| Windows 11 Widget Board integration | Requires MSIX packaging + Windows App SDK + C#; incompatible with Python/CTk stack | Microsoft docs |
| AI-generated weekly usage reports | Adds API cost + complexity for marginal insight; a sparkline achieves the same at zero cost | bozdemir widget |
| Chrome DPAPI cookie extraction | Fragile, version-coupled, legally grey, breaks on Chrome updates | Existing ROADMAP "Considering" notes |
| Full token refresh with write-back | Rotation breaks live CLI sessions; existing "opt-in safe" roadmap item is the max-safe approach | Already in Considering |

## Sources

**Competitors (GitHub):**
- https://github.com/jens-duttke/usage-monitor-for-claude
- https://github.com/steipete/CodexBar
- https://github.com/Javis603/token-monitor
- https://github.com/mm7894215/TokenTracker
- https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor
- https://github.com/bozdemir/claude-usage-widget
- https://github.com/projectvelox/claude-usage-widget
- https://github.com/ccusage/ccusage
- https://github.com/junhoyeo/tokscale
- https://github.com/Dicklesworthstone/coding_agent_usage_tracker
- https://github.com/phuryn/claude-usage
- https://github.com/sr-kai/claudeusagewin
- https://github.com/niccolo-sabato/claude-usage-widget

**Community / Pain Points:**
- https://github.com/anthropics/claude-code/issues/17431
- https://github.com/anthropics/claude-code/issues/43149
- https://github.com/anthropics/claude-code/issues/47157
- https://github.com/anthropics/claude-code/issues/68379
- https://github.com/openai/codex/issues/19732
- https://github.com/openai/codex/issues/30390
- https://github.com/openai/codex/issues/31214

**Security / Dependencies:**
- https://github.com/python-pillow/Pillow/releases
- https://github.com/pydantic/httpx2
- https://pypi.org/project/Windows-Toasts/
- https://github.com/TomSchimansky/CustomTkinter
- https://pyinstaller.org/en/stable/CHANGES.html

**UX Patterns:**
- https://alternativeto.net/software/trafficmonitor/about/
- https://bjango.com/mac/istatmenus/
- https://github.com/exelban/stats
- https://www.eleken.co/blog-posts/notification-ux

## Open Questions

1. **httpx2 stability** — Pydantic fork launched Jun 2026; is it production-stable enough for a shipped app, or should we vendor httpx 0.28.1 until httpx2 proves itself? (Needs: 2-3 months of release cadence observation)
2. **customtkinter 6.0 breaking changes** — Changelog not fully public; needs hands-on testing before upgrading from 5.2.x. (Needs: install in venv, run smoke test, check for API breaks)
3. **Codex endpoint stability** — `chatgpt.com/backend-api/wham/usage` is undocumented. Has OpenAI signaled any official usage API? If so, migration may be needed. (Needs: monitoring OpenAI developer blog/changelog)
