"""Notifications and sound.

Banners are delivered via rumps (reliable only once packaged as a .app with a
bundle id). Alarm sound loops until explicitly stopped. All macOS imports are
done lazily/guarded so this module imports cleanly on non-mac platforms (the
functions simply no-op there, which keeps the rest of the app importable for
testing).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

IS_MAC = sys.platform == "darwin"
SYSTEM_SOUNDS_DIR = Path("/System/Library/Sounds")


def notify(title: str, subtitle: str = "", message: str = "", sound: bool = False) -> None:
    """Post a notification banner. No-op off macOS."""
    if not IS_MAC:
        return
    try:
        import rumps  # local import: only available on macOS

        rumps.notification(title=title, subtitle=subtitle, message=message, sound=sound)
    except Exception:
        # Never let a notification failure crash the run loop.
        pass


def _sound_path(name: str) -> Optional[Path]:
    candidate = SYSTEM_SOUNDS_DIR / f"{name}.aiff"
    return candidate if candidate.exists() else None


class SoundPlayer:
    """Plays a named system sound, optionally looping until stopped.

    Uses NSSound when available (supports looping natively); falls back to the
    ``afplay`` CLI for a one-shot play. Off macOS it is an inert object.
    """

    def __init__(self) -> None:
        self._nssound = None
        self._afplay_proc: Optional[subprocess.Popen] = None

    def play(self, name: str, loop: bool = False) -> None:
        if not IS_MAC:
            return
        self.stop()
        try:
            from AppKit import NSSound  # type: ignore

            path = _sound_path(name)
            if path is None:
                return
            snd = NSSound.alloc().initWithContentsOfFile_byReference_(str(path), True)
            if snd is None:
                return
            snd.setLoops_(loop)
            snd.play()
            self._nssound = snd
            return
        except Exception:
            pass
        # Fallback: afplay (no native loop; loop handled by re-spawning is overkill).
        path = _sound_path(name)
        if path is not None:
            try:
                self._afplay_proc = subprocess.Popen(["afplay", str(path)])
            except Exception:
                self._afplay_proc = None

    def stop(self) -> None:
        if self._nssound is not None:
            try:
                self._nssound.stop()
            except Exception:
                pass
            self._nssound = None
        if self._afplay_proc is not None:
            try:
                self._afplay_proc.terminate()
            except Exception:
                pass
            self._afplay_proc = None


def available_sounds() -> list[str]:
    """List built-in system sound names (without extension)."""
    if not SYSTEM_SOUNDS_DIR.exists():
        # Reasonable default set so the settings UI has options even off-mac.
        return ["Glass", "Ping", "Basso", "Blow", "Bottle", "Funk", "Hero",
                "Morse", "Pop", "Purr", "Sosumi", "Submarine", "Tink"]
    return sorted(p.stem for p in SYSTEM_SOUNDS_DIR.glob("*.aiff"))
