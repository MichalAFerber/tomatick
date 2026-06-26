"""Pomodoro / general settings.

``open_settings(app)`` tries to present a native PyObjC window; if AppKit is
unavailable or the native path raises, it falls back to sequential rumps
dialogs. Either way it mutates ``app.settings`` and persists.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import widgets
from .widgets import HAVE_APPKIT

if TYPE_CHECKING:  # pragma: no cover
    from ..app import TomatickApp


def open_settings(app: "TomatickApp") -> None:
    if HAVE_APPKIT:
        try:
            _open_native(app)
            return
        except Exception as exc:  # pragma: no cover - native runtime issues
            import traceback
            traceback.print_exc()
            widgets.confirm(f"Native settings failed ({exc}); using simple dialogs.",
                            title="Tomatick")
    _open_fallback(app)


# ---------------------------------------------------------------------------
# Fallback: sequential rumps prompts
# ---------------------------------------------------------------------------
def _open_fallback(app: "TomatickApp") -> None:
    pomo = app.settings.pomodoro
    fields = [
        ("work_minutes", "Work minutes"),
        ("short_break_minutes", "Short break minutes"),
        ("long_break_minutes", "Long break minutes"),
        ("cycles_before_long_break", "Work cycles before a long break"),
    ]
    for key, label in fields:
        answer = widgets.ask_text(f"{label}:", title="Pomodoro Settings",
                                  default=str(pomo[key]))
        if answer is None:
            return  # cancelled -> abort without saving
        try:
            pomo[key] = max(1, int(answer))
        except ValueError:
            widgets.confirm(f"'{answer}' isn't a number; keeping {pomo[key]}.")

    auto = widgets.confirm("Auto-start the next pomodoro phase?",
                           title="Pomodoro Settings", ok="Yes", cancel="No")
    pomo["auto_start_next"] = auto

    sounds = app.available_sounds()
    chosen = widgets.choose("Default alarm/notification sound:", sounds,
                            title="Sound")
    if chosen:
        app.settings.data["default_sound"] = chosen

    app.settings.save()
    app.rebuild_menu()


# ---------------------------------------------------------------------------
# Native PyObjC window
# ---------------------------------------------------------------------------
def _open_native(app: "TomatickApp") -> None:
    import AppKit
    import objc
    from Foundation import NSObject, NSMakeRect

    pomo = app.settings.pomodoro

    # Build a controller lazily so PyObjC class is only defined on macOS.
    class _SettingsController(NSObject):
        def initWithApp_(self, the_app):
            self = objc.super(_SettingsController, self).init()
            if self is None:
                return None
            self._app = the_app
            self._fields = {}
            return self

        def show(self):
            rect = NSMakeRect(0, 0, 320, 260)
            style = (AppKit.NSWindowStyleMaskTitled
                     | AppKit.NSWindowStyleMaskClosable)
            win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, style, AppKit.NSBackingStoreBuffered, False)
            win.setTitle_("Tomatick Settings")
            win.setReleasedWhenClosed_(False)
            content = win.contentView()

            rows = [
                ("work_minutes", "Work minutes"),
                ("short_break_minutes", "Short break minutes"),
                ("long_break_minutes", "Long break minutes"),
                ("cycles_before_long_break", "Cycles before long break"),
            ]
            y = 220
            for key, label in rows:
                lbl = AppKit.NSTextField.alloc().initWithFrame_(
                    NSMakeRect(16, y, 190, 22))
                lbl.setStringValue_(label)
                lbl.setBezeled_(False)
                lbl.setDrawsBackground_(False)
                lbl.setEditable_(False)
                lbl.setSelectable_(False)
                content.addSubview_(lbl)

                field = AppKit.NSTextField.alloc().initWithFrame_(
                    NSMakeRect(214, y, 90, 22))
                field.setStringValue_(str(pomo[key]))
                content.addSubview_(field)
                self._fields[key] = field
                y -= 32

            auto = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(16, y, 280, 22))
            auto.setButtonType_(AppKit.NSButtonTypeSwitch)
            auto.setTitle_("Auto-start next phase")
            auto.setState_(AppKit.NSControlStateValueOn
                           if pomo.get("auto_start_next", True)
                           else AppKit.NSControlStateValueOff)
            content.addSubview_(auto)
            self._auto = auto
            y -= 40

            save = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(214, 16, 90, 30))
            save.setTitle_("Save")
            save.setBezelStyle_(AppKit.NSBezelStyleRounded)
            save.setTarget_(self)
            save.setAction_("save:")
            content.addSubview_(save)

            self._window = win
            win.center()
            win.makeKeyAndOrderFront_(None)
            AppKit.NSApp.activateIgnoringOtherApps_(True)

        def save_(self, sender):
            for key, field in self._fields.items():
                try:
                    pomo[key] = max(1, int(field.stringValue()))
                except ValueError:
                    pass
            pomo["auto_start_next"] = (
                self._auto.state() == AppKit.NSControlStateValueOn)
            self._app.settings.save()
            self._app.rebuild_menu()
            self._window.close()

    controller = _SettingsController.alloc().initWithApp_(app)
    # Keep a reference on the app so it isn't garbage collected while open.
    app._open_windows.append(controller)
    controller.show()
