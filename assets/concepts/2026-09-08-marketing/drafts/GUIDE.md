# AIUsageTracker v0.4.1 guide

## Installation and first use

Use the [Windows installer or portable ZIP](https://github.com/SysAdminDoc/AIUsageTracker/releases/tag/v0.4.1). Both contain the same application. No Python installation is needed for either download. The installer runs per user by default; desktop shortcuts and startup are optional.

Downloads are unsigned. A checksum can detect a changed download, but it isn't a code-signing certificate. Follow your organization's software policy and don't disable Windows protection to run the app.

For live usage, sign in through Claude Code or the Codex CLI first. AIUsageTracker reads those saved credentials on each poll. It doesn't accept a password and doesn't renew a login. If a token expires, reopen the relevant CLI, sign in there, and select **Refresh usage** in the dashboard.

Only using one provider? Open Settings and turn off the other. Disabling a provider stops its regular usage requests. The separate local-token summary still scans both providers' supported log locations.

## Offline preview

Run `AIUsageTracker.exe --demo` from its folder, or `python run.py --demo` from a source checkout.

The demo displays labeled example values. It doesn't load your settings or credentials, read your conversation logs, start the tray, make provider requests, save changes or play sounds. Settings changes last only for that preview session.

You can open a specific appearance or view directly:

```powershell
.\AIUsageTracker.exe --demo --demo-theme daylight
.\AIUsageTracker.exe --demo --demo-view activity
.\AIUsageTracker.exe --demo --demo-view settings
```

Demo options never turn a running preview into a live session. Close it and relaunch without `--demo` to connect normally.

## Understanding the dashboard

Percentages are **used**, not remaining. The provider determines which quota windows are returned. Some accounts have session and weekly windows; others include model-specific limits. Missing windows aren't treated as zero usage.

The top row shows the nearest upcoming reset and the highest-used window. The smaller cards count active windows, windows at or below 50%, and windows at or above 70%. Forecast hints use recent samples, so they can change quickly and aren't promises about remaining work.

Activity lists detected resets. Its heatmap shows the highest stored quota percentage per day across the sampled windows. The provider filter filters the event list, not the heatmap. History is collected while this app runs; it isn't imported from a provider's billing dashboard.

Close the main window to hide it in the tray during live mode. Use the tray's **Quit** command to stop the app. If the tray couldn't start, closing the window exits instead. **Mini mode** is available from the tray menu; double-click the overlay to return to the dashboard.

## Reset alerts

Use the bell on a quota row to enable or disable reset alerts for that window. Settings has a separate master sound switch and Windows notification switch. Six built-in sounds are available, with optional looping until you acknowledge the alert.

The regular interval defaults to 180 seconds. A known reset can schedule a check eight seconds after its boundary, but scheduled checks still respect the minimum poll interval. Manual refresh can request an earlier poll and may encounter provider throttling. Reset events received close together are grouped for five seconds.

Alerts depend on returned data. They can arrive later than the visible countdown because of polling, sleep, an expired login or a network failure. The detector looks for a reset timestamp moving forward by more than a minute. When reset timestamps are absent, a usage drop of at least 25 percentage points can also signal a reset.

## Data and privacy

| Location | What the app does |
| --- | --- |
| `%USERPROFILE%\.claude\.credentials.json` | Reads the Claude Code OAuth access token and expiry. Doesn't write or refresh it. |
| `%USERPROFILE%\.codex\auth.json` | Reads the Codex access token and expiry where available. Doesn't write or refresh it. |
| `%USERPROFILE%\.claude\projects\**\*.jsonl` | Scans recently modified session logs for token-usage objects. Log files may also contain conversation text, although only usage totals are displayed. |
| `%USERPROFILE%\.codex\logs_2.sqlite` | Opens the local log database read-only and scans recent response events for token totals. |
| `%APPDATA%\AIUsageTracker` | Writes settings, snapshot metadata, usage history, reset events, status export and cached alarm sounds. |

The recent-token summary is approximate. Claude scanning uses each file's modification time to choose recent files and may include older records in a recently updated file. Repeated usage entries can be counted more than once. Codex counts matching response events from the last 24 hours; its displayed session count is based on response identifiers. Input and output tokens contribute to the displayed total. Cache counters aren't added to it again. The summary refreshes when the dashboard is built, not on every quota poll.

Provider requests go to `api.anthropic.com/api/oauth/usage` and `chatgpt.com/backend-api/wham/usage`. The access token is sent in the authorization header for the corresponding provider. The application doesn't include its own analytics collector.

Snapshots can contain account metadata returned by a provider, including an email address. Local app files aren't encrypted by this project. Treat the directory as private. Optional webhooks transmit reset messages to a URL you supply. Optional event hooks run your command locally and can do anything that command is allowed to do.

Uninstalling the app leaves settings and history in place. If you want to remove them, quit the app first and delete only its named data folder. Never post credential files, webhook URLs, account paths or raw session logs in an issue.

## Advanced settings

Quit the app before editing `%APPDATA%\AIUsageTracker\settings.json`. Keep a backup. The Settings dialog covers themes, primary providers, sound, notifications and polling. The options below are file-based.

### Additional accounts

Add an entry to `extra_accounts` with a unique name, provider and existing credential-file path:

```json
{
  "extra_accounts": [
    {
      "name": "work",
      "provider": "claude",
      "credential_path": "C:/credentials/work-claude.json"
    }
  ]
}
```

This is an example path, not a request to copy or publish tokens. The file must use the corresponding CLI credential format. Restart after changing accounts. An extra account has its own key, such as `claude:work`, and isn't controlled by the primary provider's toggle. To disable it, remove its entry or set its full key to `false` inside `providers`.

Quota cards support extra accounts, but the summary connection count and Activity filter are centered on the two primary providers. Extra-account snapshot caching also uses account keys in filenames, which may fail on Windows when a key contains a colon. Don't rely on those cached snapshots as a backup.

### Hooks and export

`on_reset_command` and `on_threshold_command` are empty by default. They execute through the local shell when configured, with `AIU_EVENT`, `AIU_PROVIDER`, `AIU_WINDOW`, `AIU_LABEL` and `AIU_UTILIZATION` in the environment. Review a command before enabling it. Hook execution is independent of a quota row's sound-alert toggle.

`export_status` defaults to `true` and writes `current_status.json` after successful polls. It contains window metadata and percentages, not access tokens.

`webhook_url` is empty by default. The reset-alert handler sends a message when configured. Discord-shaped payloads are implemented; don't assume every generic URL or Telegram endpoint will accept the format. Live webhook delivery hasn't been verified for this release.

`warn_toast_at` defaults to 90. `window_thresholds` can override that value per window key. Set `alarm_sound_name` to `Custom` and `custom_alarm_path` to a local WAV path if you need a custom tone. These options require valid values; there's no advanced-settings editor or schema migration tool.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| Not signed in | The CLI must have a saved login at a supported path. A browser session alone doesn't provide one. |
| Login expired or HTTP 401 | Sign in again through the provider's CLI, then refresh. The app deliberately won't rotate refresh tokens. |
| HTTP 429 | Stop repeated manual refreshes and allow background polling to retry. The provider controls its rate limits. |
| Stale usage | Check connectivity and login state. The stale indicator appears after twice the configured interval. |
| Countdown passed, no alert | Wait for a confirmed reset from a successful poll. Check the bell toggle, sound setting and Windows notifications. |
| Token total differs from another tool | It's an approximate local-log summary with the limitations described above, not provider billing. |

The endpoints are undocumented. If their response format changes, [report the version and visible error](https://github.com/SysAdminDoc/AIUsageTracker/issues) without attaching private data.
