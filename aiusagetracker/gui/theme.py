"""Theme catalog and shared design tokens for the desktop dashboard."""
from __future__ import annotations

DEFAULT_THEME = "midnight"

THEME_LABELS = {
    "midnight": "Midnight",
    "graphite": "Graphite",
    "daylight": "Daylight",
}

THEME_DESCRIPTIONS = {
    "midnight": "Deep navy with coral, cyan, and mint accents.",
    "graphite": "Neutral charcoal with softer violet and blue accents.",
    "daylight": "Bright surfaces with strong, accessible contrast.",
}

THEMES = {
    "midnight": {
        "appearance": "dark",
        "colors": {
            "base": "#0b1020", "mantle": "#11182b", "crust": "#080d19",
            "surface0": "#172137", "surface1": "#22304a", "surface2": "#33415c",
            "overlay0": "#64718c", "text": "#e8edf7", "subtext1": "#b3bfd4",
            "subtext0": "#8d9ab4", "mauve": "#ff7a66", "blue": "#66d9e8",
            "sapphire": "#5bbcf4", "green": "#69e0a3", "yellow": "#f6c76a",
            "peach": "#ff9a72", "red": "#ff6678", "teal": "#62d6c5",
            "lavender": "#ff9a88",
        },
        "provider_accent": {"claude": "#e77955", "codex": "#66d9e8"},
    },
    "graphite": {
        "appearance": "dark",
        "colors": {
            "base": "#15171c", "mantle": "#1c1f26", "crust": "#101216",
            "surface0": "#272b35", "surface1": "#343a47", "surface2": "#464e5e",
            "overlay0": "#727b8f", "text": "#f0f2f7", "subtext1": "#c5cad5",
            "subtext0": "#969eaf", "mauve": "#a998ff", "blue": "#7fc8ff",
            "sapphire": "#6bb8ef", "green": "#65d6a6", "yellow": "#e8bb6a",
            "peach": "#ff9b7e", "red": "#ff7185", "teal": "#6bd5ce",
            "lavender": "#c0b6ff",
        },
        "provider_accent": {"claude": "#ff9074", "codex": "#8ed8ff"},
    },
    "daylight": {
        "appearance": "light",
        "colors": {
            "base": "#f4f7fb", "mantle": "#ffffff", "crust": "#eaf0f7",
            "surface0": "#e7edf5", "surface1": "#d6dfeb", "surface2": "#bdc9d9",
            "overlay0": "#74839a", "text": "#142033", "subtext1": "#3f4e66",
            "subtext0": "#65738a", "mauve": "#df5d4c", "blue": "#147d99",
            "sapphire": "#1977b5", "green": "#168553", "yellow": "#9a6800",
            "peach": "#c96a3c", "red": "#c83d55", "teal": "#0d7f73",
            "lavender": "#f27b69",
        },
        "provider_accent": {"claude": "#c85c3e", "codex": "#167e91"},
    },
}

THEME_CHOICES = tuple(THEME_LABELS.values())

# Mutable dictionaries let modules that import these handles see a theme change
# without being re-imported. The widget tree is rebuilt after a live switch.
MOCHA: dict[str, str] = {}
PROVIDER_ACCENT: dict[str, str] = {}
SEVERITY_COLOR: dict[str, str] = {}
STATUS_COLOR: dict[str, str] = {}
BORDER = ""
BORDER_SOFT = ""
_current_theme = DEFAULT_THEME


def normalize_theme(value: str | None) -> str:
    key = str(value or DEFAULT_THEME).strip().lower()
    # ``mocha`` existed as an unused legacy setting before themes were exposed.
    if key == "mocha":
        key = DEFAULT_THEME
    return key if key in THEMES else DEFAULT_THEME


def theme_key_from_label(label: str) -> str:
    folded = str(label).strip().casefold()
    for key, value in THEME_LABELS.items():
        if value.casefold() == folded:
            return key
    return normalize_theme(label)


def theme_label(value: str | None) -> str:
    return THEME_LABELS[normalize_theme(value)]


def palette_for(value: str | None) -> dict[str, str]:
    return THEMES[normalize_theme(value)]["colors"]


def appearance_for(value: str | None) -> str:
    return str(THEMES[normalize_theme(value)]["appearance"])


def description_for(value: str | None) -> str:
    return THEME_DESCRIPTIONS[normalize_theme(value)]


def apply_theme(value: str | None) -> str:
    """Activate a theme and update every shared color map in place."""
    global BORDER, BORDER_SOFT, _current_theme
    key = normalize_theme(value)
    spec = THEMES[key]
    MOCHA.clear()
    MOCHA.update(spec["colors"])
    PROVIDER_ACCENT.clear()
    PROVIDER_ACCENT.update(spec["provider_accent"])
    SEVERITY_COLOR.clear()
    SEVERITY_COLOR.update({
        "normal": MOCHA["green"],
        "warning": MOCHA["yellow"],
        "critical": MOCHA["red"],
    })
    STATUS_COLOR.clear()
    STATUS_COLOR.update({
        "ok": MOCHA["green"],
        "auth_expired": MOCHA["yellow"],
        "no_credentials": MOCHA["overlay0"],
        "error": MOCHA["red"],
    })
    BORDER = MOCHA["surface2"]
    BORDER_SOFT = MOCHA["surface1"]
    _current_theme = key
    return key


def current_theme() -> str:
    return _current_theme


apply_theme(DEFAULT_THEME)

# Radius tokens: softly squared controls, never pill-shaped.
R_XS = 4
R_SM = 6
R_MD = 10
R_LG = 12

# Spacing scale.
SP_XS = 4
SP_SM = 8
SP_MD = 12
SP_LG = 16
SP_XL = 24

# Typography scale tuned for desktop readability at 100-125% scaling.
FS_DISPLAY = 25
FS_H1 = 30
FS_H2 = 18
FS_TITLE = 14
FS_BODY = 12
FS_SMALL = 11
FS_TINY = 10

FONT = "Segoe UI"
