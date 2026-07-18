"""Catppuccin Mocha palette + design tokens (no pill radii; 8/10/12 only)."""
from __future__ import annotations

MOCHA = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay0": "#6c7086",
    "text": "#cdd6f4",
    "subtext1": "#bac2de",
    "subtext0": "#a6adc8",
    "mauve": "#cba6f7",
    "blue": "#89b4fa",
    "sapphire": "#74c7ec",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "peach": "#fab387",
    "red": "#f38ba8",
    "teal": "#94e2d5",
    "lavender": "#b4befe",
}

# Radius tokens (pills/ovals are banned; scale = 0/4/6/8/10/12)
R_XS = 6
R_SM = 8
R_MD = 10
R_LG = 12

# Spacing scale (consistent rhythm)
SP_XS = 4
SP_SM = 8
SP_MD = 12
SP_LG = 16
SP_XL = 24

# Typography scale (no random px values)
FS_DISPLAY = 24
FS_H1 = 20
FS_H2 = 15
FS_TITLE = 13
FS_BODY = 12
FS_SMALL = 11
FS_TINY = 10

# Surface / border layering: base < mantle < surface0 < surface1
BORDER = MOCHA["surface1"]
BORDER_SOFT = MOCHA["surface0"]

# Brand colours (used for provider accents + tiles)
CLAUDE_BRAND = "#d97757"
CODEX_BRAND = "#10a37f"

# Accent per provider (brand-aligned)
PROVIDER_ACCENT = {
    "claude": MOCHA["peach"],   # reads as Claude clay against dark UI
    "codex": MOCHA["teal"],     # reads as OpenAI green/teal against dark UI
}

SEVERITY_COLOR = {
    "normal": MOCHA["green"],
    "warning": MOCHA["yellow"],
    "critical": MOCHA["red"],
}

STATUS_COLOR = {
    "ok": MOCHA["green"],
    "auth_expired": MOCHA["yellow"],
    "no_credentials": MOCHA["overlay0"],
    "error": MOCHA["red"],
}

FONT = "Segoe UI"
