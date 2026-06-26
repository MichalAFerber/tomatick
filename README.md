# Tomatick

[![CI](https://github.com/MichalAFerber/tomatick/actions/workflows/ci.yml/badge.svg)](https://github.com/MichalAFerber/tomatick/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A macOS **menu bar** timer, stopwatch, alarm and pomodoro — all in one icon,
with a timestamped history of everything you run.

Built with [`rumps`](https://github.com/jaredks/rumps) (which wraps
`NSStatusItem`/`NSMenu`) and PyObjC. **No Xcode and no Apple Developer Program
are required** to build or run it for yourself.

## Features

- **Timer** — natural-language durations (`25m`, `1h30m`, `90s`, `2:30`), with a
  live `M:SS` countdown in the menu bar. Pause / Reset / Stop.
- **Stopwatch** — counts up, with optional laps. Pause / Reset / Stop.
- **Pomodoro** — 25/5/15 by default, auto-advancing phases (🍅 work, ☕ break),
  long break after every 4th work cycle. Pause / Skip phase / Stop.
- **Alarms** — one-shot (a specific date + time) and recurring (a time of day on
  chosen weekdays). Rings with a looping sound + notification until dismissed,
  with Snooze (9 min default).
- **Multiple at once** — run several sessions together; the menu bar shows your
  "primary" one live, and every active session is listed in the menu with its
  own count. **Pin** any session to make it the primary display.
- **History** — every event (started / paused / completed / phase change / alarm
  fired …) is timestamped into SQLite. See recent events in the menu and
  **Export** the full log to CSV or JSON.
- **Settings** — edit pomodoro durations, default sound, and toggle **Launch at
  login** (via a per-user LaunchAgent — no dev program needed). Native PyObjC
  windows, with simple dialog fallbacks if AppKit ever misbehaves.

Everything is driven from the menu bar icon's menu: start a session → it appears
in the menu → click its item to pause/stop it (or dismiss a ringing alarm).

## Download & install

Grab the latest `.dmg` from the
[**Releases**](https://github.com/MichalAFerber/tomatick/releases) page.

> **Apple Silicon only** (M1/M2/M3/M4). The build bundles an arm64 Python, so it
> won't run on Intel Macs.

1. Open the `.dmg` and drag **Tomatick** onto the **Applications** folder.
2. The bundle is unsigned, so on **first launch** right-click **Tomatick** in
   Applications → **Open** → **Open**. (A plain double-click is blocked the first
   time.) If macOS still refuses, run once in Terminal:

   ```bash
   xattr -dr com.apple.quarantine /Applications/Tomatick.app
   ```

Tomatick is a **menu bar** app — no Dock icon, no window. Look for the stopwatch
icon in the top-right menu bar. To start it at login, use the icon's menu →
**Settings → Launch at login**.

## Run it (development)

Requires **Python 3.11 or 3.12** (rumps does not yet support 3.13).

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m tomatick
```

A stopwatch icon appears in your menu bar. Click it to open the menu.

> Notifications appear reliably only from the packaged `.app` (they need a
> bundle id). From the dev script you'll still get the sounds and menu updates.

## Run the tests

The timing/scheduling/history logic has no macOS dependencies, so the tests run
anywhere (this is what CI runs on Linux):

```bash
pip install pytest
python -m pytest
```

## Build a standalone app

```bash
pip install py2app
python setup.py py2app
open dist/Tomatick.app
```

`LSUIElement` keeps it out of the Dock — it's a pure menu bar app. The bundle is
unsigned; on first launch, right-click the app in Finder → **Open** to get past
Gatekeeper. To start it automatically at login, use **Settings → Launch at
login** inside the app (or drag the app into System Settings → General → Login
Items).

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push to
`main` and on pull requests:

- **Logic tests (Linux)** — the platform-independent suite on Python 3.11 and
  3.12 (only `pytest` is needed; the macOS-only runtime deps are skipped here).
- **Import smoke + tests (macOS)** — installs the full runtime (rumps/PyObjC),
  confirms `tomatick.app` imports, and re-runs the suite.

## Where data lives

```
~/Library/Application Support/Tomatick/
├── config.json     # pomodoro settings, alarms, sound, launch-at-login
└── history.db      # SQLite event history
```

## Project layout

```
tomatick/
├── sessions.py      # Timer / Stopwatch / Pomodoro (pure logic)
├── alarms.py        # Alarm model + scheduling (pure logic)
├── history.py       # SQLite history store
├── settings.py      # config.json load/save
├── notifications.py # banners + looping sound
├── launch_agent.py  # launch-at-login LaunchAgent
├── app.py           # rumps app: menu, 1s tick, wiring
└── ui/              # native PyObjC windows + rumps fallbacks
```

## License

Released under the [MIT License](LICENSE) — © 2026 Michal Ferber.

Menu bar icons are from Flaticon's clock set —
<https://www.flaticon.com/free-icons/clock>. Flaticon's free license requires
attribution (credited here and in the app's About box). See
[`tomatick/assets/README.md`](tomatick/assets/README.md) for how to add them;
until they're present the app falls back to emoji in the menu bar.
