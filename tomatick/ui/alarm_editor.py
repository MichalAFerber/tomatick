"""Add / edit / delete alarms.

``open_alarm_editor(app)`` presents a native PyObjC window listing alarms with
Add / Edit / Delete buttons (the per-alarm field editing reuses reliable rumps
dialogs). If AppKit is unavailable or the native window raises, it falls back to
a fully dialog-driven loop. Both paths mutate ``app`` via add/update/delete
helpers and persist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .. import alarms as alarms_mod
from ..alarms import Alarm, ONE_SHOT, RECURRING, WEEKDAY_NAMES
from . import widgets
from .widgets import HAVE_APPKIT

if TYPE_CHECKING:  # pragma: no cover
    from ..app import TomatickApp


# ---------------------------------------------------------------------------
# Shared dialog-based field editor (used by both native and fallback paths)
# ---------------------------------------------------------------------------
_DAY_PRESETS = {
    "daily": [0, 1, 2, 3, 4, 5, 6],
    "weekdays": [0, 1, 2, 3, 4],
    "weekends": [5, 6],
}


def _parse_days(text: str) -> Optional[list[int]]:
    text = text.strip().lower()
    if not text:
        return []
    if text in _DAY_PRESETS:
        return _DAY_PRESETS[text]
    names = {n.lower(): i for i, n in enumerate(WEEKDAY_NAMES)}
    out = []
    for token in text.replace(" ", "").split(","):
        if token in names:
            out.append(names[token])
        else:
            return None  # signal parse error
    return sorted(set(out))


def edit_alarm_dialog(app: "TomatickApp", existing: Optional[Alarm]) -> Optional[Alarm]:
    """Prompt for all alarm fields. Returns a new/updated Alarm, or None if
    cancelled. Does not persist; the caller decides add vs update."""
    a = existing or Alarm(sound=app.settings.default_sound)

    label = widgets.ask_text("Alarm label:", title="Alarm", default=a.label)
    if label is None:
        return None
    a.label = label

    kind = widgets.choose("Alarm type:", ["One-shot (specific date)",
                                          "Recurring (days of week)"],
                          title="Alarm")
    if kind is None:
        return None
    a.kind = ONE_SHOT if kind.startswith("One-shot") else RECURRING

    time_str = widgets.ask_text("Time (HH:MM, 24-hour):", title="Alarm",
                                default=a.time_str)
    if time_str is None:
        return None
    try:
        h, m = (int(x) for x in time_str.split(":"))
        assert 0 <= h < 24 and 0 <= m < 60
        a.time_str = f"{h:02d}:{m:02d}"
    except (ValueError, AssertionError):
        widgets.confirm(f"'{time_str}' is not a valid HH:MM time.")
        return None

    if a.kind == ONE_SHOT:
        date_str = widgets.ask_text("Date (YYYY-MM-DD):", title="Alarm",
                                    default=a.date_str or "")
        if date_str is None:
            return None
        a.date_str = date_str.strip()
        a.days_of_week = []
    else:
        days_text = widgets.ask_text(
            "Days (e.g. 'weekdays', 'daily', 'weekends', or 'Mon,Wed,Fri'):",
            title="Alarm",
            default=",".join(WEEKDAY_NAMES[d] for d in a.days_of_week))
        if days_text is None:
            return None
        parsed = _parse_days(days_text)
        if parsed is None:
            widgets.confirm(f"Couldn't understand days: '{days_text}'.")
            return None
        a.days_of_week = parsed
        a.date_str = None

    sound = widgets.choose("Sound:", app.available_sounds(), title="Alarm")
    if sound:
        a.sound = sound

    a.enabled = True
    a.compute_next_fire()
    return a


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def open_alarm_editor(app: "TomatickApp") -> None:
    if HAVE_APPKIT:
        try:
            _open_native(app)
            return
        except Exception as exc:  # pragma: no cover - native runtime issues
            import traceback
            traceback.print_exc()
            widgets.confirm(f"Native alarm editor failed ({exc}); using dialogs.")
    _open_fallback(app)


# ---------------------------------------------------------------------------
# Fallback loop
# ---------------------------------------------------------------------------
def _open_fallback(app: "TomatickApp") -> None:
    while True:
        listing = [a.menu_text() for a in app.alarms]
        options = ["➕ Add new alarm"] + listing + ["✓ Done"]
        choice = widgets.choose("Manage alarms:", options, title="Alarms")
        if choice is None or choice == "✓ Done":
            return
        if choice == "➕ Add new alarm":
            new = edit_alarm_dialog(app, None)
            if new:
                app.add_alarm(new)
            continue
        # An existing alarm was chosen.
        idx = listing.index(choice)
        alarm = app.alarms[idx]
        action = widgets.choose(f"'{alarm.label or 'Alarm'}':",
                                ["Edit", "Delete", "Toggle on/off"],
                                title="Alarm")
        if action == "Edit":
            updated = edit_alarm_dialog(app, alarm)
            if updated:
                app.update_alarm(updated)
        elif action == "Delete":
            if widgets.confirm("Delete this alarm?", ok="Delete"):
                app.delete_alarm(alarm.id)
        elif action == "Toggle on/off":
            alarm.enabled = not alarm.enabled
            app.update_alarm(alarm)


# ---------------------------------------------------------------------------
# Native window: table list + Add / Edit / Delete
# ---------------------------------------------------------------------------
_ALARM_CONTROLLER = None  # PyObjC class; registered once per process


def _open_native(app: "TomatickApp") -> None:
    cls = _alarm_controller_class()
    controller = cls.alloc().initWithApp_(app)
    app._open_windows.append(controller)
    controller.show()


def _alarm_controller_class():
    """Define the controller class once and cache it (see settings_window for
    why: a PyObjC class name may only be registered once per process)."""
    global _ALARM_CONTROLLER
    if _ALARM_CONTROLLER is not None:
        return _ALARM_CONTROLLER

    import AppKit
    import objc
    from Foundation import NSObject, NSMakeRect

    class _AlarmController(NSObject):
        def initWithApp_(self, the_app):
            self = objc.super(_AlarmController, self).init()
            if self is None:
                return None
            self._app = the_app
            return self

        # NSTableView data source -----------------------------------------
        def numberOfRowsInTableView_(self, table):
            return len(self._app.alarms)

        def tableView_objectValueForTableColumn_row_(self, table, col, row):
            alarm = self._app.alarms[row]
            return alarm.menu_text()

        # Window ----------------------------------------------------------
        def show(self):
            rect = NSMakeRect(0, 0, 420, 300)
            style = (AppKit.NSWindowStyleMaskTitled
                     | AppKit.NSWindowStyleMaskClosable)
            win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, style, AppKit.NSBackingStoreBuffered, False)
            win.setTitle_("Alarms")
            win.setReleasedWhenClosed_(False)
            content = win.contentView()

            scroll = AppKit.NSScrollView.alloc().initWithFrame_(
                NSMakeRect(16, 60, 388, 220))
            scroll.setHasVerticalScroller_(True)
            scroll.setBorderType_(AppKit.NSBezelBorder)

            table = AppKit.NSTableView.alloc().initWithFrame_(
                NSMakeRect(0, 0, 388, 220))
            col = AppKit.NSTableColumn.alloc().initWithIdentifier_("alarm")
            col.setWidth_(370)
            col.setTitle_("Alarm")
            table.addTableColumn_(col)
            table.setDataSource_(self)
            table.setDelegate_(self)
            scroll.setDocumentView_(table)
            content.addSubview_(scroll)
            self._table = table

            specs = [("Add", "add:", 16), ("Edit", "edit:", 116),
                     ("Delete", "delete:", 216)]
            for title, action, x in specs:
                btn = AppKit.NSButton.alloc().initWithFrame_(
                    NSMakeRect(x, 16, 90, 30))
                btn.setTitle_(title)
                btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
                btn.setTarget_(self)
                btn.setAction_(action)
                content.addSubview_(btn)

            self._window = win
            win.center()
            win.makeKeyAndOrderFront_(None)
            AppKit.NSApp.activateIgnoringOtherApps_(True)

        def _reload(self):
            self._table.reloadData()

        def add_(self, sender):
            new = edit_alarm_dialog(self._app, None)
            if new:
                self._app.add_alarm(new)
            self._reload()

        def edit_(self, sender):
            row = self._table.selectedRow()
            if row < 0:
                return
            alarm = self._app.alarms[row]
            updated = edit_alarm_dialog(self._app, alarm)
            if updated:
                self._app.update_alarm(updated)
            self._reload()

        def delete_(self, sender):
            row = self._table.selectedRow()
            if row < 0:
                return
            alarm = self._app.alarms[row]
            if widgets.confirm("Delete this alarm?", ok="Delete"):
                self._app.delete_alarm(alarm.id)
            self._reload()

    _ALARM_CONTROLLER = _AlarmController
    return _ALARM_CONTROLLER
