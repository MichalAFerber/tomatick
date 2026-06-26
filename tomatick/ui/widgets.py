"""Shared UI helpers and rumps-dialog fallbacks.

The native PyObjC windows (settings_window, alarm_editor) call into these
fallbacks whenever AppKit is unavailable or a native path raises. The fallbacks
use only ``rumps.Window`` / ``rumps.alert`` and therefore work everywhere rumps
runs.
"""

from __future__ import annotations

import sys
from typing import List, Optional

IS_MAC = sys.platform == "darwin"

try:  # AppKit only exists on macOS with PyObjC installed.
    import AppKit  # type: ignore  # noqa: F401
    HAVE_APPKIT = True
except Exception:  # pragma: no cover - non-mac
    HAVE_APPKIT = False


def ask_text(message: str, title: str = "Tomatick", default: str = "",
             ok: str = "OK", cancel: str = "Cancel") -> Optional[str]:
    """Prompt for a single line of text via rumps. Returns None if cancelled."""
    import rumps

    win = rumps.Window(
        message=message,
        title=title,
        default_text=default,
        ok=ok,
        cancel=cancel,
        dimensions=(280, 24),
    )
    response = win.run()
    if response.clicked:
        return response.text.strip()
    return None


def confirm(message: str, title: str = "Tomatick", ok: str = "OK",
            cancel: str = "Cancel") -> bool:
    import rumps

    return bool(rumps.alert(title=title, message=message, ok=ok, cancel=cancel))


def choose(message: str, options: List[str], title: str = "Tomatick") -> Optional[str]:
    """Pick one of ``options`` by typing its number. Simple but dependency-free."""
    listing = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
    answer = ask_text(f"{message}\n\n{listing}\n\nEnter a number:", title=title)
    if answer is None:
        return None
    try:
        idx = int(answer) - 1
    except ValueError:
        return None
    if 0 <= idx < len(options):
        return options[idx]
    return None
