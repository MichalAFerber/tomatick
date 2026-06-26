"""Settings load/save tests with a redirected support dir."""

import json

from tomatick.settings import DEFAULTS, Settings


def test_defaults_present():
    s = Settings()
    assert s.pomodoro["work_minutes"] == 25
    assert s.snooze_minutes == 9
    assert s.launch_at_login is False


def test_deep_merge_backfills_new_defaults():
    # Simulate an old config missing newer keys.
    s = Settings({"snooze_minutes": 5, "pomodoro": {"work_minutes": 50}})
    assert s.snooze_minutes == 5                       # user value kept
    assert s.pomodoro["work_minutes"] == 50            # user value kept
    assert s.pomodoro["short_break_minutes"] == 5      # default backfilled


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TOMATICK_SUPPORT_DIR", str(tmp_path))
    s = Settings.load()
    s.data["snooze_minutes"] = 3
    s.set("default_sound", "Ping")
    reloaded = Settings.load()
    assert reloaded.snooze_minutes == 3
    assert reloaded.default_sound == "Ping"
    # File is valid JSON on disk.
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["default_sound"] == "Ping"
