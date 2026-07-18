# ROADMAP

Single source of truth for open work. Legend: 🤖 = autonomous-codeable, 🔧 = operator/product-gated.

## Next

- 🤖 **Reset history view** — in-app panel/tab listing past resets from `reset_events.jsonl` with per-window filtering.
- 🤖 **Frameless always-on-top widget mode** — compact desktop widget variant (drag-to-move, opacity, remembers position) in addition to the full window.
- 🤖 **Per-window warn thresholds** — currently a single global `warn_toast_at`; allow a custom threshold per usage bar next to its alarm toggle.
- 🤖 **Custom alarm sound file** — let users point at their own `.wav` in addition to the six built-in tones.
- 🤖 **Autostart on login** — optional Startup-folder / HKCU Run entry toggle in Settings.
- 🤖 **Focus rings / keyboard-nav pass** — CTk focus visibility is minimal; add visible focus states and verify tab order for accessibility.
- 🤖 **Snooze / one-window acknowledge** — acknowledge a single window's alarm without silencing others.
- 🤖 **Source health check** — surface a warning when an endpoint stops returning a valid `resets_at` (schema drift early-warning), per the research note.
- 🤖 **ccusage-style token/cost view** — read local `~/.claude/projects/**/*.jsonl` and `~/.codex/state_5.sqlite` for token/cost totals to complement the account-window view.

## Considering

- 🔧 **Cookie/session fallback for CLI-less users** — support users who only use the web apps (no Claude Code / Codex CLI) via a manual `sessionKey` paste or Firefox cookie import. Deliberately avoids Chrome v20 app-bound DPAPI decryption.
- 🔧 **Gemini / other providers** — generalize the provider interface to add more quota sources.
- 🔧 **Optional token refresh (opt-in, safe)** — refresh-and-verify-to-a-copy before writing back, to keep polling when the CLIs aren't running. Gated because refresh-token rotation risks the live CLI login.

## Research-Driven Additions (2026-07-18)

- [ ] P1 — **Dynamic tray icon (severity color + % text)**
  Why: Users must open the full window to see usage status. Competitors (TrafficMonitor, Pomodoro timers, iStat Menus) render live data INTO the tray icon for instant glanceability.
  Evidence: jens-duttke/usage-monitor-for-claude uses color-coded tray; community signal #1 is "I want to know without clicking."
  Touches: `gui/app.py` (tray icon update loop), `gui/icons.py` (new `tray_status_icon()` renderer)
  Acceptance: Tray icon updates every poll cycle showing highest-usage % as text or green→yellow→orange→red color gradient.
  Complexity: M

- [ ] P1 — **Burn-rate / ETA-to-exhaustion forecast**
  Why: Community's biggest unmet need after threshold alerts — "at current pace, when will I hit the wall?" Multiple competitors (Claude-Code-Usage-Monitor, bozdemir widget, CodexBar) offer this.
  Evidence: GitHub issues #41930, #55779; Claude-Code-Usage-Monitor P90 calculator; 232-upvote Reddit thread on surprise mid-task halts.
  Touches: `poller.py` (track utilization deltas over time), `models.py` (add `burn_rate` field), `gui/app.py` (display ETA in StatCard)
  Acceptance: Dashboard shows "~Xh Ym until limit" based on rolling rate-of-change; updates each poll cycle.
  Complexity: M

- [ ] P1 — **Event hooks (shell command on reset/threshold)**
  Why: Power users want to trigger automation on reset (auto-resume Claude Code, send notification to phone, log to file). Direct competitor (jens-duttke) ships this.
  Evidence: jens-duttke/usage-monitor-for-claude "event commands"; community request for agent self-pacing (issue #43149).
  Touches: `config.py` (new `on_reset_command`, `on_threshold_command` settings), `poller.py` (subprocess.Popen on event)
  Acceptance: User can configure a shell command in Settings that executes when any window resets; command receives provider/window/utilization as args.
  Complexity: M

- [ ] P2 — **Usage sparklines in LimitRow cards**
  Why: Current bars show point-in-time snapshot only. A tiny sparkline (last 24h of polls) shows trend — is usage accelerating or flat? Competitors (CodexBar, phuryn/claude-usage) ship inline charts.
  Evidence: CodexBar inline spend charts; phuryn/claude-usage Chart.js graphs; community demand for history (Product Hunt 239 upvotes).
  Touches: `storage.py` (persist poll snapshots to time-series store), `gui/app.py` (CTkCanvas sparkline widget in each LimitRow)
  Acceptance: Each usage bar has a ~100x20px sparkline showing last 24h of utilization readings; updates on each poll.
  Complexity: L

- [ ] P2 — **Historical usage persistence (time-series store)**
  Why: Enables sparklines, heatmaps, burn-rate calculation, and trend analysis. Current storage only keeps reset events, not utilization readings over time.
  Evidence: Required foundation for sparklines, ETA forecast, and calendar heatmap features. phuryn/claude-usage and token-monitor both persist historical data.
  Touches: `storage.py` (new `append_snapshot()` writing timestamped utilization to `usage_history.jsonl` or SQLite), `config.py` (retention policy setting)
  Acceptance: Every successful poll appends a timestamped record; records older than 30 days auto-pruned; file stays under 5MB.
  Complexity: M

- [ ] P2 — **Alert aggregation (group simultaneous resets)**
  Why: When Claude and Codex windows reset within 60s of each other, user gets 2+ separate alarms back-to-back. Should consolidate into one "Both tools reset" notification.
  Evidence: Notification UX best practice (PagerDuty, Icinga alert-fatigue guides); iStat Menus groups alerts.
  Touches: `poller.py` or `gui/app.py` (debounce/group pending reset events within 60s window before alarming)
  Acceptance: Two resets within 60s produce one grouped alarm/toast/banner instead of two separate ones.
  Complexity: S

- [ ] P2 — **PyInstaller exe size reduction**
  Why: 45MB is large for a monitoring widget. Competitors achieve 2-6MB. Clean venv + UPX + module exclusions can reach ~20MB.
  Evidence: jens-duttke at ~2MB (compiled TS); claudeusagewin at ~6MB (.NET). PyInstaller docs on --exclude-module + UPX.
  Touches: `build.ps1` (add UPX path, exclude unused modules), new `build.spec` (explicit excludes for scipy/numpy/test/email/xmlrpc/unused Pillow plugins)
  Acceptance: `dist\AIUsageTracker.exe` under 25MB without functionality loss.
  Complexity: M

- [ ] P2 — **Multiple account/credential support**
  Why: Power users run 2+ Claude/Codex subscriptions to workaround rate limits; need fast switching or simultaneous monitoring.
  Evidence: Medium article "Running Two Claude Code Subs Side by Side"; community discussions on multi-profile workarounds.
  Touches: `auth.py` (accept list of credential paths), `config.py` (accounts[] setting), `gui/app.py` (account selector or multi-card layout)
  Acceptance: User can add multiple credential file paths in Settings; each account appears as a separate provider card.
  Complexity: L

- [ ] P2 — **Data freshness indicator**
  Why: Users need to trust the displayed data is current, not stale from a failed poll. "Last polled: 47s ago" or a pulse animation builds confidence.
  Evidence: Azure quota dashboards show last-updated timestamps; Vercel shows "refreshed X ago"; real-time dashboard UX best practices.
  Touches: `gui/app.py` (add "Last updated Xs ago" to topbar or each ProviderCard; subtle pulse animation on successful poll)
  Acceptance: Dashboard shows relative time since last successful poll; stale data (>2x poll interval) shows a warning badge.
  Complexity: S

- [ ] P3 — **Calendar heatmap in Activity view**
  Why: Reveals daily/weekly usage patterns (which hours are heavy, which days hit limits). GitHub-style contribution graphs are universally understood.
  Evidence: GitHub contribution heatmap; tokscale 2D contributions graph; data visualization best practices.
  Touches: `gui/app.py` (new heatmap widget in Activity view), `storage.py` (query usage_history by day/hour)
  Acceptance: Activity view shows a 7-row × N-week grid color-coded by daily peak utilization; tooltip shows exact values.
  Complexity: L

- [ ] P3 — **Export usage data to env var / named pipe (agent integration)**
  Why: Autonomous coding agents (Claude Code /loop, Codex background) could self-pace if they knew remaining quota. Community issue #43149 requests exactly this.
  Evidence: GitHub issue anthropics/claude-code#43149 ("Expose API usage limits and rate-limit reset timer"); jens-duttke event hooks.
  Touches: `config.py` (enable/disable export), `poller.py` (write `AI_USAGE_PCT` / `AI_RESET_AT` env vars or a well-known temp file on each poll)
  Acceptance: A file at `%APPDATA%\AIUsageTracker\current_status.json` is updated every poll with provider/utilization/resets_at; agents can read it.
  Complexity: M

- [ ] P3 — **Telegram / Discord alert forwarding**
  Why: Users are often AFK (phone, different PC) when limits reset. Push notification to phone ensures they resume immediately.
  Evidence: en4ble1337/codex-usage-monitor ships Discord/Telegram alerts; Javis603/token-monitor has Discord Rich Presence.
  Touches: `config.py` (webhook URL settings), `alarm.py` (new `forward_alert()` that POSTs to webhook on reset)
  Acceptance: User configures a Discord/Telegram webhook URL in Settings; reset events trigger a POST with provider + window + utilization info.
  Complexity: M

- [ ] P3 — **Animated bar transitions**
  Why: Abrupt bar jumps on poll updates feel jarring. Smooth 200-400ms easing makes updates feel responsive and polished.
  Evidence: iStat Menus, Vercel dashboards, real-time dashboard UX best practices (Smashing Magazine).
  Touches: `gui/app.py` (animate CTkProgressBar value changes via `after()` frame interpolation)
  Acceptance: Usage bars animate smoothly between old and new values over ~300ms on each poll update.
  Complexity: S

## Done

### v0.2.0
- Brand tiles for Claude (sunburst) and Codex (hexafoil) + new app mark.
- Six selectable, synthesized alarm sounds with a Settings picker + Test preview.
- Premium polish pass: design tokens, card borders/elevation, severity edges,
  refined Settings (sections + hints), microcopy across states, row-height fix.

### v0.1.0
- Claude + Codex usage polling via local OAuth tokens.
- Timestamp-driven reset detection + boundary-scheduled polling.
- Audible alarm + toast + in-app banner on reset.
- Per-bar alarm toggles.
- customtkinter GUI, tray, settings, headless CLI, tests, PyInstaller build.
