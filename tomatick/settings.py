"""Configuration storage for Tomatick.

Settings live in ``~/Library/Application Support/Tomatick/config.json``. This
module is intentionally free of any macOS/AppKit imports so it can be unit
tested on any platform.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

APP_NAME = "Tomatick"
BUNDLE_ID = "us.tomatick"

# Default configuration. ``alarms`` holds a list of serialized Alarm dicts (see
# alarms.Alarm.to_dict). Everything here is plain JSON-serializable data.
DEFAULTS: Dict[str, Any] = {
    "pomodoro": {
        "work_minutes": 25,
        "short_break_minutes": 5,
        "long_break_minutes": 15,
        "cycles_before_long_break": 4,
        "auto_start_next": True,
    },
    "snooze_minutes": 9,
    "default_sound": "Glass",  # one of the built-in /System/Library/Sounds names
    "launch_at_login": False,
    "alarms": [],
    # Quick-start timer presets: list of {"label", "seconds"}.
    "presets": [
        {"label": "Focus", "seconds": 1500},
        {"label": "Quick break", "seconds": 300},
    ],
    # Focus / Do-Not-Disturb via macOS Shortcuts (run by name; "" = disabled).
    "focus_shortcut_on": "",
    "focus_shortcut_off": "",
    "focus_during_work": True,
    # Single global hotkey: action id + key-combo symbol string ("" = none).
    "hotkey_action": "none",
    "hotkey_key": "",
    # Menu-bar icon theme: red | white | black.
    "icon_theme": "red",
}


def support_dir() -> Path:
    """Return the per-user Application Support directory, creating it if needed.

    Honors ``TOMATICK_SUPPORT_DIR`` so tests can redirect storage to a temp dir.
    """
    override = os.environ.get("TOMATICK_SUPPORT_DIR")
    if override:
        base = Path(override)
    else:
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_path() -> Path:
    return support_dir() / "config.json"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``override`` onto a copy of ``base``."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Settings:
    """Loads, exposes and persists the JSON config, backfilling new defaults."""

    def __init__(self, data: Dict[str, Any] | None = None):
        self.data: Dict[str, Any] = _deep_merge(DEFAULTS, data or {})

    @classmethod
    def load(cls) -> "Settings":
        path = config_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                raw = {}
        else:
            raw = {}
        return cls(raw)

    def save(self) -> None:
        config_path().write_text(json.dumps(self.data, indent=2, sort_keys=True))

    def normalize(self) -> None:
        """Backfill any missing defaults (e.g. after importing a partial config)."""
        self.data = _deep_merge(DEFAULTS, self.data)

    # Convenience accessors -------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    @property
    def pomodoro(self) -> Dict[str, Any]:
        return self.data["pomodoro"]

    @property
    def snooze_minutes(self) -> int:
        return int(self.data["snooze_minutes"])

    @property
    def default_sound(self) -> str:
        return self.data["default_sound"]

    @property
    def launch_at_login(self) -> bool:
        return bool(self.data["launch_at_login"])
