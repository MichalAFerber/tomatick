"""Trigger macOS Focus / Do-Not-Disturb via the Shortcuts app.

macOS has no public API to toggle Focus, so we run user-created Shortcuts by
name (``shortcuts run "<name>"``). Best effort: a missing/empty name is a no-op.
"""

from __future__ import annotations

import subprocess


def run_shortcut(name: str) -> bool:
    """Run a Shortcut by name. Returns True if it was launched."""
    name = (name or "").strip()
    if not name:
        return False
    try:
        subprocess.run(["shortcuts", "run", name], timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:  # pragma: no cover - shortcuts missing / errored
        return False
