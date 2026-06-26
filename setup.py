"""py2app build configuration for Tomatick.

Build the app bundle (on macOS):

    python setup.py py2app

The result is ``dist/Tomatick.app``. ``LSUIElement`` keeps it out of the Dock
so it lives purely in the menu bar. No Apple Developer Program is required to
build or run it locally; on first launch use Finder → right-click → Open to get
past Gatekeeper for the unsigned bundle.
"""

from pathlib import Path

from setuptools import setup

HERE = Path(__file__).parent
ASSETS = HERE / "tomatick" / "assets"

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
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
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
