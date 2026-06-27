---
---

# Tomatick — Quick Start

A macOS **menu bar** timer, stopwatch, alarm and pomodoro — all in one icon,
with a timestamped history of everything you run.

> **Requirements:** Apple Silicon Mac (M1/M2/M3/M4), a recent macOS. The build is
> unsigned (no Apple Developer Program needed).

---

## 1. Install

1. Download the latest **`Tomatick-x.y.z.dmg`** from the
   [**Releases**](https://github.com/MichalAFerber/tomatick/releases) page.
2. Open the `.dmg` and drag **Tomatick** onto the **Applications** folder.
3. **First launch only:** right-click **Tomatick** in Applications →
   **Open** → **Open**. (A plain double-click is blocked the first time because
   the app is unsigned.) If macOS still refuses, run once in Terminal:

   ```bash
   xattr -dr com.apple.quarantine /Applications/Tomatick.app
   ```

Tomatick is a **menu bar app** — there's no Dock icon and no window. Look for the
🍅 (or stopwatch) icon in the **top-right menu bar**. Click it for everything.

---

## 2. Start something

Click the menu bar icon → **Start**:

- **Timer** — type a natural duration: `25m`, `1h30m`, `90s`, `2:30`, or a bare
  number (minutes). A live `M:SS` countdown shows in the menu bar.
- **Stopwatch** — counts up; supports laps.
- **Pomodoro** — 25 / 5 / 15 by default, auto-advancing work ↔ break, with a long
  break after every 4th work cycle.
- **Alarm** — one-shot (a date + time) or recurring (a time on chosen weekdays).

Every running session is listed in the menu. Click a session for **Pause/Resume**
and **Stop**, plus **Reset** (timer & stopwatch), **Skip phase** (pomodoro) or
**Lap** (stopwatch) — and **Pin** to make its countdown the one in the menu bar.

**When a timer finishes it keeps ringing** (looping sound + a `⏱ … · done` entry)
until you click **Dismiss** — so you won't miss it.

---

## 3. Presets (one-click timers)

Save the timers you start often (it ships with **Focus 25:00** and
**Quick break 5:00**):

- **Use one:** Start menu → pick a preset under the divider.
- **Manage them:** Settings → **Presets** tab → Add / Edit / Delete (name +
  duration like `25m`).

---

## 4. Settings

Open **Settings…** from the menu — one window with tabs:

| Tab | What's in it |
|-----|--------------|
| **General** | Default sound, snooze minutes, **global hotkey**, launch at login, **Export / Import Settings** |
| **Pomodoro** | Work / break lengths, auto-start, **Focus during work** |
| **Presets** | Manage quick-start timers |
| **Alarms** | Add / edit / delete alarms |
| **History** | Full event log (newest first) — **Export** to CSV/JSON, **Clear** |
| **About** | Version, credits, links |

General and Pomodoro fields apply on **Save**; Presets, Alarms and import apply
immediately.

---

## 5. Focus / Do-Not-Disturb during work

Tomatick can turn a macOS **Focus** on while you're in a pomodoro **work** phase
and off on breaks. macOS has no public API for this, so it runs **Shortcuts you
create**:

1. Open the **Shortcuts** app → **+** to create a new shortcut.
2. Add the action **Set Focus** → choose your Focus (e.g. *Do Not Disturb*) →
   **Turn On**. Name it e.g. **`Tomatick Focus On`**.
3. Make a second shortcut that **Turns Off** that Focus, e.g.
   **`Tomatick Focus Off`**.
4. In Tomatick → Settings → **Pomodoro** tab, type those exact names into
   **Focus Shortcut (on)** / **(off)** and tick **Trigger Focus during work
   phases**. Save.

Leave the names blank to disable the feature.

---

## 6. Global hotkey

Settings → **General** → **Global hotkey**: pick an **action** (Start Pomodoro,
Start Timer, or Toggle Keep Awake) and a **key** (e.g. `⌥⌘P`). Save.

> The first time you use it, macOS asks to grant **Tomatick** **Accessibility**
> permission (System Settings → Privacy & Security → Accessibility). Until you
> allow it, the hotkey simply won't fire.

---

## 7. Keep Awake

Menu → **Keep awake** prevents your Mac from sleeping while it's on (great during
a long task). You can also bind it to the global hotkey. It turns itself off when
you quit.

---

## 8. Copy your setup to another Mac

Configure one Mac, then mirror it everywhere:

1. Settings → **General** → **Export Settings…** → save the `.json`.
2. On the other Mac: Settings → **General** → **Import Settings…** → pick that
   file.

This copies your presets, pomodoro lengths, sounds, snooze, Focus shortcut names,
hotkey, and alarms. (Launch-at-login is left per-machine and isn't copied.)

---

## Where your data lives

```
~/Library/Application Support/Tomatick/
├── config.json     # all settings, presets, alarms
└── history.db      # SQLite event history
```

---

Questions or bugs? See the
[GitHub repository](https://github.com/MichalAFerber/tomatick).
