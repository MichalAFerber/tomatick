"""Launch-at-login via a per-user LaunchAgent.

Writes/removes ``~/Library/LaunchAgents/us.tomatick.plist``. This requires no
Apple Developer Program membership. When running from a packaged .app we point
the agent at the app bundle via ``open``; in dev we point it at the current
Python interpreter running ``-m tomatick``.
"""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .settings import BUNDLE_ID

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def plist_path() -> Path:
    return LAUNCH_AGENTS_DIR / f"{BUNDLE_ID}.plist"


def _program_arguments(app_path: Optional[str]) -> List[str]:
    """Determine the command the LaunchAgent should run."""
    if app_path:
        # Launch the bundled .app without bringing it to the foreground.
        return ["/usr/bin/open", "-g", app_path]
    # Dev fallback: re-run this package with the current interpreter.
    return [sys.executable, "-m", "tomatick"]


def is_installed() -> bool:
    return plist_path().exists()


def install(app_path: Optional[str] = None) -> Path:
    """Create the LaunchAgent plist and load it. Returns the plist path."""
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "Label": BUNDLE_ID,
        "ProgramArguments": _program_arguments(app_path),
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    path = plist_path()
    with path.open("wb") as fh:
        plistlib.dump(data, fh)
    _launchctl("load", str(path))
    return path


def uninstall() -> None:
    """Unload and remove the LaunchAgent plist if present."""
    path = plist_path()
    if path.exists():
        _launchctl("unload", str(path))
        try:
            path.unlink()
        except OSError:
            pass


def _launchctl(action: str, plist: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(["launchctl", action, plist], check=False,
                       capture_output=True)
    except Exception:
        pass


def set_enabled(enabled: bool, app_path: Optional[str] = None) -> None:
    if enabled:
        install(app_path)
    else:
        uninstall()
