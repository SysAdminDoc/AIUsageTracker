# Parked product decisions

These aren't promised features.

## Accounts without a CLI

Browser-session import would need an explicit, safe credential-handling design. The current app requires a saved Claude Code or Codex CLI login.

## Additional providers

Gemini and other providers need a documented data source and maintained parser before being offered as supported integrations.

## Token refresh

Automatic refresh remains deliberately disabled. Rotating a refresh token can invalidate a CLI's active login. Don't add write-back without a tested isolation and recovery plan.
