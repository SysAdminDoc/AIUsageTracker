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

# Radius tokens (pills/ovals are banned)
R_SM = 8
R_MD = 10
R_LG = 12

# Accent per provider
PROVIDER_ACCENT = {
    "claude": MOCHA["peach"],
    "codex": MOCHA["teal"],
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
