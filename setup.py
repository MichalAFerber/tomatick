"""py2app build configuration for Tomatick.

Build the app bundle (on macOS):

    python setup.py py2app

The result is ``dist/Tomatick.app``. ``LSUIElement`` keeps it out of the Dock
so it lives purely in the menu bar. No Apple Developer Program is required to
build or run it locally; on first launch use Finder → right-click → Open to get
past Gatekeeper for the unsigned bundle.
"""

import re
from pathlib import Path

from setuptools import setup

HERE = Path(__file__).parent
ASSETS = HERE / "tomatick" / "assets"

# Single source of truth for the version: tomatick/__init__.py.
_VERSION_MATCH = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (HERE / "tomatick" / "__init__.py").read_text(),
)
if not _VERSION_MATCH:
    raise RuntimeError(
        'Could not find __version__ in tomatick/__init__.py '
        '(expected: __version__ = "X.Y.Z").')
VERSION = _VERSION_MATCH.group(1)

APP = ["run_tomatick.py"]

DATA_FILES = []
if ASSETS.exists():
    icon_files = [str(p) for p in ASSETS.glob("*.png")]
    if icon_files:
        DATA_FILES.append(("assets", icon_files))

icns = ASSETS / "tomatick.icns"

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,                 # menu-bar only, no Dock icon
        "CFBundleName": "Tomatick",
        "CFBundleDisplayName": "Tomatick",
        "CFBundleIdentifier": "us.tomatick",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHumanReadableCopyright": "Icons by Flaticon.",
    },
    "packages": ["rumps", "tomatick"],
}
if icns.exists():
    OPTIONS["iconfile"] = str(icns)

setup(
    app=APP,
    name="Tomatick",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
