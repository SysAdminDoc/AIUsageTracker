from aiusagetracker import config
from aiusagetracker.demo import DemoSession


def test_demo_uses_only_in_memory_examples(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Demo touched live storage")

    monkeypatch.setattr(config, "data_dir", forbidden)
    session = DemoSession()
    received = []
    session.on_snapshot = received.append
    session.start()
    session.poll_now()
    session.stop()
    assert len(received) == 4
    assert len(session.history) == 28
    assert session.stats.total == 306000
    assert all(s.meta == {"plan_type": "Example"} for s in received)
    assert session.settings["alarm_sound"] is False
    assert session.settings["toast"] is False
    assert session.settings["webhook_url"] == ""


def test_demo_settings_do_not_mutate_defaults_or_other_sessions():
    first, second = DemoSession(), DemoSession("daylight")
    first.settings["window_alarms"]["claude:session"] = False
    assert "claude:session" not in second.settings["window_alarms"]
    assert "claude:session" not in config.DEFAULT_SETTINGS["window_alarms"]
    assert second.settings["theme"] == "daylight"
