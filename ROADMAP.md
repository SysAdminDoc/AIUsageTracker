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

- [ ] P2 — **Multiple account/credential support**
  Why: Power users run 2+ Claude/Codex subscriptions to workaround rate limits; need fast switching or simultaneous monitoring.
  Evidence: Medium article "Running Two Claude Code Subs Side by Side"; community discussions on multi-profile workarounds.
  Touches: `auth.py` (accept list of credential paths), `config.py` (accounts[] setting), `gui/app.py` (account selector or multi-card layout)
  Acceptance: User can add multiple credential file paths in Settings; each account appears as a separate provider card.
  Complexity: L

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
