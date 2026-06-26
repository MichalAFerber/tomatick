"""TomatickApp — the rumps menu bar application.

This module imports rumps/AppKit and therefore only runs on macOS. It owns:
  * the active sessions (timers / stopwatches / pomodoros),
  * the alarm definitions and their firing,
  * a single 1-second tick that advances everything on the main run loop,
  * the dynamic menu, history logging, notifications and sound.

Pure logic lives in sessions.py / alarms.py / history.py / settings.py, which
have no macOS dependencies and are unit tested separately.
"""

from __future__ import annotations

import os
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

import rumps

from . import launch_agent
from .alarms import Alarm, load_alarms
from .history import History
from .notifications import SoundPlayer, available_sounds, notify
from .sessions import (DONE, PAUSED, RUNNING, Pomodoro, Stopwatch, Timer,
                       parse_duration)
from .settings import APP_NAME, Settings, support_dir
from .ui import alarm_editor, settings_window

ASSETS = Path(__file__).parent / "assets"


class TomatickApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title="🍅", quit_button=None)

        self.settings = Settings.load()
        self.history = History()
        self.alarms = load_alarms(self.settings.data.get("alarms", []))

        # Active sessions keyed by id, preserving start order.
        self.sessions: "OrderedDict[int, object]" = OrderedDict()
        self._session_items: dict[int, rumps.MenuItem] = {}
        self._pinned_id: int | None = None

        # Alarms currently ringing, and snoozed re-fires.
        self.firing_alarms: list[dict] = []   # {alarm, item}
        self._snoozes: list[dict] = []         # {fire_at, label, sound}

        self.alarm_player = SoundPlayer()   # looping ring
        self.cue_player = SoundPlayer()     # one-shot cues

        # Menu-bar icons (template images adapt to light/dark menu bars).
        self._idle_icon = self._asset("idle.png")
        self._running_icon = self._asset("running.png")
        self.template = True

        self._open_windows: list = []  # keep PyObjC window controllers alive

        self.rebuild_menu()
        self._update_title()

        self.timer = rumps.Timer(self.on_tick, 1)
        self.timer.start()

    # ------------------------------------------------------------------ utils
    def _asset(self, name: str) -> str | None:
        path = ASSETS / name
        return str(path) if path.exists() else None

    def available_sounds(self):
        return available_sounds()

    def log(self, kind, action, label=None, details=None, duration_s=None):
        self.history.log_event(kind, action, label=label, details=details,
                               duration_s=duration_s)

    # --------------------------------------------------------------- menu build
    def rebuild_menu(self):
        self._session_items.clear()
        self.menu.clear()
        m = []

        # Start ----------------------------------------------------------
        start_children = [
            rumps.MenuItem("Timer…", callback=self.start_timer),
            rumps.MenuItem("Stopwatch", callback=self.start_stopwatch),
            rumps.MenuItem("Pomodoro", callback=self.start_pomodoro),
            rumps.MenuItem("Alarm…", callback=self.open_alarms),
        ]
        m.append([rumps.MenuItem("Start"), start_children])
        m.append(None)

        # Active sessions + ringing alarms -------------------------------
        if self.sessions or self.firing_alarms:
            m.append(rumps.MenuItem("Active"))  # no callback -> disabled header
            for sess in self.sessions.values():
                parent = rumps.MenuItem(sess.menu_text())
                self._session_items[sess.id] = parent
                m.append([parent, self._session_submenu(sess)])
            for fa in self.firing_alarms:
                alarm = fa["alarm"]
                parent = rumps.MenuItem(f"🔔 {alarm.label or 'Alarm'} · ringing")
                children = [
                    rumps.MenuItem("Dismiss",
                                   callback=lambda s, a=alarm: self.dismiss_alarm(a)),
                    rumps.MenuItem("Snooze",
                                   callback=lambda s, a=alarm: self.snooze_alarm(a)),
                ]
                m.append([parent, children])
            m.append(None)

        # History --------------------------------------------------------
        hist_children = []
        recent = self.history.recent(self.settings.get("history_recent_count", 10))
        if recent:
            for row in recent:
                ts = row["ts"].replace("T", " ")
                name = row["label"] or row["kind"]
                hist_children.append(
                    rumps.MenuItem(f"{ts}  {name} · {row['action']}"))
        else:
            empty = rumps.MenuItem("(no events yet)")
            hist_children.append(empty)
        hist_children.append(None)
        hist_children.append(rumps.MenuItem("Export…", callback=self.export_history))
        hist_children.append(rumps.MenuItem("Clear history", callback=self.clear_history))
        m.append([rumps.MenuItem("History"), hist_children])
        m.append(None)

        # Settings -------------------------------------------------------
        launch_item = rumps.MenuItem("Launch at login", callback=self.toggle_launch)
        launch_item.state = 1 if self.settings.launch_at_login else 0

        sound_children = []
        for s in self.available_sounds():
            si = rumps.MenuItem(s, callback=self.set_sound)
            si.state = 1 if s == self.settings.default_sound else 0
            sound_children.append(si)

        settings_children = [
            rumps.MenuItem("Pomodoro…", callback=self.open_settings),
            rumps.MenuItem("Alarms…", callback=self.open_alarms),
            launch_item,
            [rumps.MenuItem("Sound"), sound_children],
        ]
        m.append([rumps.MenuItem("Settings"), settings_children])
        m.append(None)

        m.append(rumps.MenuItem("About", callback=self.about))
        m.append(rumps.MenuItem("Quit", callback=rumps.quit_application))

        self.menu.update(m)

    def _session_submenu(self, sess):
        is_pomodoro = isinstance(sess, Pomodoro)
        toggle_title = "Resume" if sess.state == PAUSED else "Pause"
        items = [rumps.MenuItem(toggle_title,
                                callback=lambda s, x=sess: self.session_toggle(x))]
        if is_pomodoro:
            items.append(rumps.MenuItem("Skip phase",
                                        callback=lambda s, x=sess: self.session_skip(x)))
        else:
            items.append(rumps.MenuItem("Reset",
                                        callback=lambda s, x=sess: self.session_reset(x)))
        if isinstance(sess, Stopwatch):
            items.append(rumps.MenuItem("Lap",
                                        callback=lambda s, x=sess: self.session_lap(x)))
        items.append(rumps.MenuItem("Stop",
                                    callback=lambda s, x=sess: self.session_stop(x)))
        pin = rumps.MenuItem("Pin as primary",
                             callback=lambda s, x=sess: self.session_pin(x))
        pin.state = 1 if self._pinned_id == sess.id else 0
        items.append(pin)
        return items

    # ----------------------------------------------------------------- starting
    def start_timer(self, _):
        from .ui import widgets
        text = widgets.ask_text("Duration (e.g. 25m, 1h30m, 90s):", title="Timer")
        if text is None:
            return
        try:
            seconds = parse_duration(text)
        except ValueError:
            widgets.confirm(f"Couldn't understand '{text}'.")
            return
        if seconds <= 0:
            return
        label = widgets.ask_text("Label (optional):", title="Timer") or ""
        sess = Timer(seconds, label=label)
        self._add_session(sess)
        self.log("timer", "started", label=label, duration_s=seconds)

    def start_stopwatch(self, _):
        from .ui import widgets
        label = widgets.ask_text("Label (optional):", title="Stopwatch") or ""
        sess = Stopwatch(label=label)
        self._add_session(sess)
        self.log("stopwatch", "started", label=label)

    def start_pomodoro(self, _):
        from .ui import widgets
        label = widgets.ask_text("Label (optional):", title="Pomodoro") or ""
        sess = Pomodoro(self.settings.pomodoro, label=label)
        self._add_session(sess)
        self.log("pomodoro", "started", label=label)

    def _add_session(self, sess):
        self.sessions[sess.id] = sess
        self._pinned_id = sess.id  # newest becomes primary
        self.rebuild_menu()
        self._update_title()

    # ------------------------------------------------------------ session actions
    def session_toggle(self, sess):
        action = sess.toggle_pause()
        if action:
            self.log(sess.kind, action, label=sess.label)
        self.rebuild_menu()
        self._update_title()

    def session_reset(self, sess):
        sess.reset()
        self.log(sess.kind, "reset", label=sess.label)
        self.rebuild_menu()
        self._update_title()

    def session_skip(self, sess):
        for ev in sess.skip_phase():
            self.log(ev["kind"], ev["action"], label=ev.get("label"),
                     details=ev.get("details"))
        self._notify_phase(sess)
        self.rebuild_menu()
        self._update_title()

    def session_lap(self, sess):
        elapsed = sess.lap()
        self.log(sess.kind, "lap", label=sess.label, details={"elapsed_s": elapsed})

    def session_stop(self, sess):
        self.log(sess.kind, "stopped", label=sess.label)
        self._remove_session(sess.id)

    def session_pin(self, sess):
        self._pinned_id = sess.id
        self.rebuild_menu()
        self._update_title()

    def _remove_session(self, sid):
        self.sessions.pop(sid, None)
        if self._pinned_id == sid:
            self._pinned_id = next(reversed(self.sessions), None)
        self.rebuild_menu()
        self._update_title()

    # ------------------------------------------------------------------- ticking
    def on_tick(self, _):
        structural_change = False

        # Advance sessions.
        completed = []
        for sess in list(self.sessions.values()):
            events = sess.tick(1)
            for ev in events:
                self.log(ev["kind"], ev["action"], label=ev.get("label"),
                         details=ev.get("details"), duration_s=ev.get("duration_s"))
                if ev["action"] == "completed":
                    completed.append(sess)
                    self._notify_complete(sess)
                elif ev["action"] == "phase_change":
                    self._notify_phase(sess)
                    structural_change = True  # icon/label may change
            # Update live title in place when no rebuild is pending.
            item = self._session_items.get(sess.id)
            if item is not None:
                item.title = sess.menu_text()

        for sess in completed:
            self.sessions.pop(sess.id, None)
            if self._pinned_id == sess.id:
                self._pinned_id = next(reversed(self.sessions), None)
            structural_change = True

        # Fire alarms & snoozes.
        if self._check_alarms():
            structural_change = True

        if structural_change:
            self.rebuild_menu()
        self._update_title()

    def _check_alarms(self) -> bool:
        now = datetime.now()
        changed = False

        for alarm in self.alarms:
            if (alarm.enabled and alarm.next_fire is not None
                    and alarm.next_fire <= now
                    and not any(f["alarm"] is alarm for f in self.firing_alarms)):
                self._fire_alarm(alarm, now)
                changed = True

        # Snoozed re-fires.
        still = []
        for snz in self._snoozes:
            if snz["fire_at"] <= now:
                self._fire_snooze(snz)
                changed = True
            else:
                still.append(snz)
        self._snoozes = still
        return changed

    def _fire_alarm(self, alarm, now):
        self.firing_alarms.append({"alarm": alarm})
        self.log("alarm", "alarm_fired", label=alarm.label)
        notify("Alarm", subtitle=alarm.label or "", message=alarm.describe())
        self.alarm_player.play(alarm.sound or self.settings.default_sound, loop=True)
        alarm.mark_fired(now)
        self._persist_alarms()

    def _fire_snooze(self, snz):
        # Represent a snoozed alarm as a lightweight transient firing entry.
        transient = Alarm(label=snz["label"], sound=snz["sound"])
        transient.enabled = False
        self.firing_alarms.append({"alarm": transient})
        self.log("alarm", "alarm_fired", label=snz["label"], details={"snoozed": True})
        notify("Alarm (snoozed)", subtitle=snz["label"] or "", message="")
        self.alarm_player.play(snz["sound"] or self.settings.default_sound, loop=True)

    def dismiss_alarm(self, alarm):
        self.firing_alarms = [f for f in self.firing_alarms if f["alarm"] is not alarm]
        self.log("alarm", "alarm_dismissed", label=alarm.label)
        if not self.firing_alarms:
            self.alarm_player.stop()
        self.rebuild_menu()
        self._update_title()

    def snooze_alarm(self, alarm):
        mins = self.settings.snooze_minutes
        self.firing_alarms = [f for f in self.firing_alarms if f["alarm"] is not alarm]
        self._snoozes.append({
            "fire_at": datetime.now() + timedelta(minutes=mins),
            "label": alarm.label,
            "sound": alarm.sound,
        })
        self.log("alarm", "snoozed", label=alarm.label, details={"minutes": mins})
        if not self.firing_alarms:
            self.alarm_player.stop()
        self.rebuild_menu()
        self._update_title()

    # ---------------------------------------------------------------- notifying
    def _notify_complete(self, sess):
        notify("Timer done", subtitle=sess.label or "", message="Time's up!")
        self.cue_player.play(self.settings.default_sound, loop=False)

    def _notify_phase(self, sess):
        phase = sess.phase.replace("_", " ")
        notify("Pomodoro", subtitle=sess.label or "", message=f"Now: {phase}")
        self.cue_player.play(self.settings.default_sound, loop=False)

    # ------------------------------------------------------------------- title
    def _primary(self):
        if self._pinned_id in self.sessions:
            return self.sessions[self._pinned_id]
        for sess in reversed(self.sessions.values()):
            if sess.state == RUNNING:
                return sess
        return next(reversed(self.sessions.values()), None) if self.sessions else None

    def _update_title(self):
        primary = self._primary()
        if self._idle_icon and self._running_icon:
            self.icon = self._running_icon if primary else self._idle_icon
            self.title = primary.title_text() if primary else ""
        else:
            self.icon = None
            self.title = (f"{primary.icon} {primary.title_text()}"
                          if primary else "🍅")

    # --------------------------------------------------------------- alarm CRUD
    def add_alarm(self, alarm):
        self.alarms.append(alarm)
        self._persist_alarms()
        self.rebuild_menu()

    def update_alarm(self, alarm):
        alarm.compute_next_fire()
        for i, a in enumerate(self.alarms):
            if a.id == alarm.id:
                self.alarms[i] = alarm
                break
        self._persist_alarms()
        self.rebuild_menu()

    def delete_alarm(self, alarm_id):
        self.alarms = [a for a in self.alarms if a.id != alarm_id]
        self._persist_alarms()
        self.rebuild_menu()

    def _persist_alarms(self):
        self.settings.data["alarms"] = [a.to_dict() for a in self.alarms]
        self.settings.save()

    # ------------------------------------------------------------------ windows
    def open_settings(self, _):
        settings_window.open_settings(self)

    def open_alarms(self, _):
        alarm_editor.open_alarm_editor(self)

    # ----------------------------------------------------------------- history
    def export_history(self, _):
        from .ui import widgets
        fmt = widgets.choose("Export format:", ["CSV", "JSON"], title="Export History")
        if not fmt:
            return
        desktop = Path.home() / "Desktop"
        out_dir = desktop if desktop.exists() else support_dir()
        if fmt == "CSV":
            path = self.history.export_csv(out_dir / "tomatick_history.csv")
        else:
            path = self.history.export_json(out_dir / "tomatick_history.json")
        widgets.confirm(f"Exported {self.history.count()} events to:\n{path}",
                        title="Export History")

    def clear_history(self, _):
        from .ui import widgets
        if widgets.confirm("Delete all history events?", ok="Delete"):
            self.history.clear()
            self.rebuild_menu()

    # ---------------------------------------------------------------- settings
    def set_sound(self, sender):
        self.settings.data["default_sound"] = sender.title
        self.settings.save()
        self.cue_player.play(sender.title, loop=False)  # preview
        self.rebuild_menu()

    def toggle_launch(self, sender):
        new_value = not self.settings.launch_at_login
        try:
            launch_agent.set_enabled(new_value, app_path=self._bundle_path())
        except Exception as exc:  # pragma: no cover
            from .ui import widgets
            widgets.confirm(f"Couldn't update launch-at-login: {exc}")
            return
        self.settings.data["launch_at_login"] = new_value
        self.settings.save()
        self.rebuild_menu()

    def _bundle_path(self) -> str | None:
        # When frozen in a .app, the executable lives under *.app/Contents/MacOS.
        exe = Path(sys.executable)
        for parent in exe.parents:
            if parent.suffix == ".app":
                return str(parent)
        return None

    def about(self, _):
        rumps.alert(
            title=f"{APP_NAME}",
            message=(
                "A menu bar timer, stopwatch, alarm and pomodoro.\n\n"
                "Menu bar icons by Flaticon (https://www.flaticon.com/free-icons/clock).\n"
                "Built with rumps + PyObjC."
            ),
        )


def main():
    TomatickApp().run()


if __name__ == "__main__":  # pragma: no cover
    main()
