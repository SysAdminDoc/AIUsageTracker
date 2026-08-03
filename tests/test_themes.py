from aiusagetracker import config
from aiusagetracker.gui import theme


def test_legacy_and_unknown_theme_values_use_midnight():
    assert config.normalize_theme("mocha") == "midnight"
    assert config.normalize_theme("unknown") == "midnight"
    assert config.normalize_theme("DAYLIGHT") == "daylight"


def test_every_theme_populates_the_shared_palette():
    required = {
        "base", "mantle", "crust", "surface0", "surface1", "surface2",
        "overlay0", "text", "subtext1", "subtext0", "mauve", "blue",
        "green", "yellow", "red", "teal", "lavender",
    }
    try:
        for key in theme.THEMES:
            assert theme.apply_theme(key) == key
            assert required <= theme.MOCHA.keys()
            assert theme.appearance_for(key) in {"dark", "light"}
            assert set(theme.PROVIDER_ACCENT) == {"claude", "codex"}
    finally:
        theme.apply_theme(theme.DEFAULT_THEME)


def test_theme_labels_round_trip_to_storage_keys():
    for key, label in theme.THEME_LABELS.items():
        assert theme.theme_key_from_label(label) == key
        assert theme.theme_label(key) == label
