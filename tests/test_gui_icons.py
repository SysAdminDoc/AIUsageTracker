from aiusagetracker.gui.icons import line_icon


def test_dashboard_line_icons_render_at_requested_size():
    names = {
        "dashboard", "activity", "refresh", "settings", "clock",
        "history", "trend", "healthy", "pressure",
    }
    for name in names:
        image = line_icon(name, size=24, color="#66d9e8")
        assert image.mode == "RGBA"
        assert image.size == (24, 24)
        assert image.getbbox() is not None
