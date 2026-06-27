"""All Tomatick settings in one modal window.

``open_settings(app)`` presents a single native PyObjC window with three tabs —
General, Pomodoro and Alarms — run modally (Save / Cancel). General and Pomodoro
fields apply only on Save; the Alarms tab edits the list in place (each add/edit
goes through its own dialog and persists immediately, matching the standalone
alarm editor). If AppKit is unavailable or the native path raises, it falls back
to sequential rumps dialogs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import widgets
from .widgets import HAVE_APPKIT
from .. import hotkey
from ..sessions import format_clock

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

    snooze = widgets.ask_text("Snooze minutes:", title="General",
                              default=str(app.settings.snooze_minutes))
    if snooze is not None:
        try:
            app.settings.data["snooze_minutes"] = max(1, int(snooze))
        except ValueError:
            pass

    on_name = widgets.ask_text("Focus 'on' Shortcut name (blank = off):",
                               title="Focus", default=app.settings.get("focus_shortcut_on", ""))
    if on_name is not None:
        app.settings.data["focus_shortcut_on"] = on_name.strip()
    off_name = widgets.ask_text("Focus 'off' Shortcut name (blank = off):",
                                title="Focus", default=app.settings.get("focus_shortcut_off", ""))
    if off_name is not None:
        app.settings.data["focus_shortcut_off"] = off_name.strip()
    app.settings.data["focus_during_work"] = widgets.confirm(
        "Trigger Focus during pomodoro work phases?", title="Focus",
        ok="Yes", cancel="No")

    want_login = widgets.confirm("Launch Tomatick at login?",
                                 title="General", ok="Yes", cancel="No")
    if want_login != app.settings.launch_at_login:
        try:
            app.apply_launch_at_login(want_login)
        except Exception as exc:  # pragma: no cover
            widgets.confirm(f"Couldn't update launch-at-login: {exc}")

    app.settings.save()
    app.rebuild_menu()


# ---------------------------------------------------------------------------
# Native PyObjC window: tabbed (General / Pomodoro / Alarms), modal
# ---------------------------------------------------------------------------
_SETTINGS_CONTROLLER = None  # PyObjC class; registered once per process


def _open_native(app: "TomatickApp") -> None:
    cls = _settings_controller_class()
    controller = cls.alloc().initWithApp_(app)
    # Keep a reference alive across the (blocking) modal session.
    app._open_windows.append(controller)
    controller.show()
    app._open_windows.remove(controller)


def _settings_controller_class():
    """Define the controller class once and cache it.

    PyObjC registers each NSObject subclass with the Objective-C runtime by
    name, and a name may only be registered once per process. Defining the class
    on every open raises "overriding existing Objective-C class" the second time
    Settings is opened, so we build it lazily and reuse it.
    """
    global _SETTINGS_CONTROLLER
    if _SETTINGS_CONTROLLER is not None:
        return _SETTINGS_CONTROLLER

    import AppKit
    import objc
    from Foundation import NSObject, NSMakeRect

    from .alarm_editor import edit_alarm_dialog
    from .preset_editor import edit_preset_dialog

    class _SettingsController(NSObject):
        def initWithApp_(self, the_app):
            self = objc.super(_SettingsController, self).init()
            if self is None:
                return None
            self._app = the_app
            self._pomo_fields = {}
            self._history_rows = []
            self._history_table = None
            self._preset_table = None
            return self

        # -- small view-builder helpers -----------------------------------
        @objc.python_method
        def _label(self, text, x, y, w):
            lbl = AppKit.NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, 22))
            lbl.setStringValue_(text)
            lbl.setBezeled_(False)
            lbl.setDrawsBackground_(False)
            lbl.setEditable_(False)
            lbl.setSelectable_(False)
            return lbl

        @objc.python_method
        def _textfield(self, value, x, y, w):
            f = AppKit.NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, 22))
            f.setStringValue_(str(value))
            return f

        @objc.python_method
        def _read_int(self, field, current, minimum=1):
            try:
                return max(minimum, int(field.stringValue()))
            except (ValueError, TypeError):
                return current

        # -- NSTableView data source (Alarms + History + Presets tabs) ----
        def numberOfRowsInTableView_(self, table):
            if table == self._history_table:
                return len(self._history_rows)
            if table == self._preset_table:
                return len(self._app.settings.get("presets", []))
            return len(self._app.alarms)

        def tableView_objectValueForTableColumn_row_(self, table, col, row):
            if table == self._history_table:
                return self._history_rows[row]
            if table == self._preset_table:
                p = self._app.settings.get("presets", [])[row]
                return f"{p['label']}  {format_clock(int(p['seconds']))}"
            return self._app.alarms[row].menu_text()

        # -- build & run --------------------------------------------------
        def show(self):
            W, H = 520, 470
            style = (AppKit.NSWindowStyleMaskTitled
                     | AppKit.NSWindowStyleMaskClosable)
            win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, W, H), style, AppKit.NSBackingStoreBuffered, False)
            win.setTitle_("Tomatick Settings")
            win.setReleasedWhenClosed_(False)
            win.setDelegate_(self)
            content = win.contentView()

            tabs = AppKit.NSTabView.alloc().initWithFrame_(
                NSMakeRect(12, 56, W - 24, H - 72))
            content.addSubview_(tabs)
            cr = tabs.contentRect()
            cw, ch = cr.size.width, cr.size.height

            tabs.addTabViewItem_(self._general_tab(cw, ch))
            tabs.addTabViewItem_(self._pomodoro_tab(cw, ch))
            tabs.addTabViewItem_(self._presets_tab(cw, ch))
            tabs.addTabViewItem_(self._alarms_tab(cw, ch))
            tabs.addTabViewItem_(self._history_tab(cw, ch))
            tabs.addTabViewItem_(self._about_tab(cw, ch))

            cancel = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(W - 200, 14, 90, 30))
            cancel.setTitle_("Cancel")
            cancel.setBezelStyle_(AppKit.NSBezelStyleRounded)
            cancel.setKeyEquivalent_("\x1b")  # Esc
            cancel.setTarget_(self)
            cancel.setAction_("cancel:")
            content.addSubview_(cancel)

            save = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(W - 104, 14, 90, 30))
            save.setTitle_("Save")
            save.setBezelStyle_(AppKit.NSBezelStyleRounded)
            save.setKeyEquivalent_("\r")  # Return = default button
            save.setTarget_(self)
            save.setAction_("save:")
            content.addSubview_(save)

            self._window = win
            win.center()
            AppKit.NSApp.activateIgnoringOtherApps_(True)
            AppKit.NSApp.runModalForWindow_(win)  # blocks until close
            win.orderOut_(None)

        @objc.python_method
        def _tab_view(self, identifier, label, cw, ch):
            item = AppKit.NSTabViewItem.alloc().initWithIdentifier_(identifier)
            item.setLabel_(label)
            view = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, cw, ch))
            item.setView_(view)
            return item, view

        @objc.python_method
        def _general_tab(self, cw, ch):
            item, view = self._tab_view("general", "General", cw, ch)
            y = ch - 44

            view.addSubview_(self._label("Default sound:", 16, y, 110))
            popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(132, y - 2, cw - 148, 26), False)
            popup.addItemsWithTitles_(self._app.available_sounds())
            popup.selectItemWithTitle_(self._app.settings.default_sound)
            popup.setTarget_(self)
            popup.setAction_("previewSound:")
            view.addSubview_(popup)
            self._sound = popup
            y -= 40

            view.addSubview_(self._label("Menu bar icon:", 16, y, 110))
            mb = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(132, y - 2, cw - 148, 26), False)
            mb.addItemsWithTitles_(["Red", "White", "Black"])
            mb.selectItemWithTitle_(
                self._app.settings.get("icon_theme", "red").capitalize())
            view.addSubview_(mb)
            self._mb_theme = mb
            y -= 40

            view.addSubview_(self._label("Snooze minutes:", 16, y, 130))
            self._snooze = self._textfield(self._app.settings.snooze_minutes,
                                           150, y, 70)
            view.addSubview_(self._snooze)
            y -= 40

            view.addSubview_(self._label("Global hotkey:", 16, y, 110))
            act = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(132, y - 2, cw - 148, 26), False)
            act.addItemsWithTitles_([lbl for _, lbl in hotkey.HOTKEY_ACTIONS])
            cur_action = self._app.settings.get("hotkey_action", "none")
            act.selectItemWithTitle_(dict(hotkey.HOTKEY_ACTIONS).get(cur_action,
                                                                     "(disabled)"))
            view.addSubview_(act)
            self._hk_action = act
            y -= 38

            view.addSubview_(self._label("Hotkey key:", 16, y, 110))
            keyp = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(132, y - 2, cw - 148, 26), False)
            keyp.addItemsWithTitles_(
                ["(none)" if k == "" else k for k in hotkey.HOTKEY_KEYS])
            cur_key = self._app.settings.get("hotkey_key", "")
            keyp.selectItemWithTitle_("(none)" if cur_key == "" else cur_key)
            view.addSubview_(keyp)
            self._hk_key = keyp
            y -= 40

            launch = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(16, y, cw - 32, 22))
            launch.setButtonType_(AppKit.NSButtonTypeSwitch)
            launch.setTitle_("Launch Tomatick at login")
            launch.setState_(AppKit.NSControlStateValueOn
                             if self._app.settings.launch_at_login
                             else AppKit.NSControlStateValueOff)
            view.addSubview_(launch)
            self._launch = launch
            y -= 40

            exp = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(16, y, 150, 28))
            exp.setTitle_("Export Settings…")
            exp.setBezelStyle_(AppKit.NSBezelStyleRounded)
            exp.setTarget_(self)
            exp.setAction_("exportSettings:")
            view.addSubview_(exp)

            imp = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(174, y, 150, 28))
            imp.setTitle_("Import Settings…")
            imp.setBezelStyle_(AppKit.NSBezelStyleRounded)
            imp.setTarget_(self)
            imp.setAction_("importSettings:")
            view.addSubview_(imp)
            return item

        def exportSettings_(self, sender):
            self._app.export_settings()

        def importSettings_(self, sender):
            if self._app.import_settings():
                self._window.close()  # reopen to see imported values

        @objc.python_method
        def _pomodoro_tab(self, cw, ch):
            pomo = self._app.settings.pomodoro
            item, view = self._tab_view("pomodoro", "Pomodoro", cw, ch)
            rows = [
                ("work_minutes", "Work minutes"),
                ("short_break_minutes", "Short break minutes"),
                ("long_break_minutes", "Long break minutes"),
                ("cycles_before_long_break", "Cycles before long break"),
            ]
            y = ch - 44
            for key, label in rows:
                view.addSubview_(self._label(label, 16, y, 200))
                field = self._textfield(pomo[key], 224, y, 80)
                view.addSubview_(field)
                self._pomo_fields[key] = field
                y -= 34

            auto = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(16, y - 4, cw - 32, 22))
            auto.setButtonType_(AppKit.NSButtonTypeSwitch)
            auto.setTitle_("Auto-start next phase")
            auto.setState_(AppKit.NSControlStateValueOn
                           if pomo.get("auto_start_next", True)
                           else AppKit.NSControlStateValueOff)
            view.addSubview_(auto)
            self._auto = auto
            y -= 38

            view.addSubview_(self._label("Focus Shortcut (on):", 16, y, 160))
            self._focus_on = self._textfield(
                self._app.settings.get("focus_shortcut_on", ""), 184, y, cw - 200)
            view.addSubview_(self._focus_on)
            y -= 32
            view.addSubview_(self._label("Focus Shortcut (off):", 16, y, 160))
            self._focus_off = self._textfield(
                self._app.settings.get("focus_shortcut_off", ""), 184, y, cw - 200)
            view.addSubview_(self._focus_off)
            y -= 36

            fdw = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(16, y, cw - 32, 22))
            fdw.setButtonType_(AppKit.NSButtonTypeSwitch)
            fdw.setTitle_("Trigger Focus during work phases")
            fdw.setState_(AppKit.NSControlStateValueOn
                          if self._app.settings.get("focus_during_work", True)
                          else AppKit.NSControlStateValueOff)
            view.addSubview_(fdw)
            self._focus_during = fdw
            return item

        @objc.python_method
        def _alarms_tab(self, cw, ch):
            item, view = self._tab_view("alarms", "Alarms", cw, ch)

            specs = [("Add", "addAlarm:", 16), ("Edit", "editAlarm:", 112),
                     ("Delete", "deleteAlarm:", 208)]
            for title, action, x in specs:
                btn = AppKit.NSButton.alloc().initWithFrame_(
                    NSMakeRect(x, 8, 90, 28))
                btn.setTitle_(title)
                btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
                btn.setTarget_(self)
                btn.setAction_(action)
                view.addSubview_(btn)

            scroll = AppKit.NSScrollView.alloc().initWithFrame_(
                NSMakeRect(12, 46, cw - 24, ch - 58))
            scroll.setHasVerticalScroller_(True)
            scroll.setBorderType_(AppKit.NSBezelBorder)
            table = AppKit.NSTableView.alloc().initWithFrame_(
                NSMakeRect(0, 0, cw - 24, ch - 58))
            col = AppKit.NSTableColumn.alloc().initWithIdentifier_("alarm")
            col.setWidth_(cw - 44)
            col.setTitle_("Alarm")
            table.addTableColumn_(col)
            table.setDataSource_(self)
            table.setDelegate_(self)
            scroll.setDocumentView_(table)
            view.addSubview_(scroll)
            self._table = table
            return item

        @objc.python_method
        def _presets_tab(self, cw, ch):
            item, view = self._tab_view("presets", "Presets", cw, ch)

            specs = [("Add", "addPreset:", 16), ("Edit", "editPreset:", 112),
                     ("Delete", "deletePreset:", 208)]
            for title, action, x in specs:
                btn = AppKit.NSButton.alloc().initWithFrame_(
                    NSMakeRect(x, 8, 90, 28))
                btn.setTitle_(title)
                btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
                btn.setTarget_(self)
                btn.setAction_(action)
                view.addSubview_(btn)

            scroll = AppKit.NSScrollView.alloc().initWithFrame_(
                NSMakeRect(12, 46, cw - 24, ch - 58))
            scroll.setHasVerticalScroller_(True)
            scroll.setBorderType_(AppKit.NSBezelBorder)
            table = AppKit.NSTableView.alloc().initWithFrame_(
                NSMakeRect(0, 0, cw - 24, ch - 58))
            col = AppKit.NSTableColumn.alloc().initWithIdentifier_("preset")
            col.setWidth_(cw - 44)
            col.setTitle_("Preset")
            col.setEditable_(False)
            table.addTableColumn_(col)
            table.setDataSource_(self)
            scroll.setDocumentView_(table)
            view.addSubview_(scroll)
            self._preset_table = table
            return item

        def addPreset_(self, sender):
            new = edit_preset_dialog(self._app, None)
            if new:
                self._app.add_preset(new)
            self._preset_table.reloadData()

        def editPreset_(self, sender):
            row = self._preset_table.selectedRow()
            if row < 0:
                return
            presets = self._app.settings.get("presets", [])
            updated = edit_preset_dialog(self._app, presets[row])
            if updated:
                self._app.update_preset(row, updated)
            self._preset_table.reloadData()

        def deletePreset_(self, sender):
            row = self._preset_table.selectedRow()
            if row < 0:
                return
            if widgets.confirm("Delete this preset?", ok="Delete"):
                self._app.delete_preset(row)
            self._preset_table.reloadData()

        @objc.python_method
        def _history_tab(self, cw, ch):
            item, view = self._tab_view("history", "History", cw, ch)

            export = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(16, 8, 110, 28))
            export.setTitle_("Export…")
            export.setBezelStyle_(AppKit.NSBezelStyleRounded)
            export.setTarget_(self)
            export.setAction_("exportHistory:")
            view.addSubview_(export)

            clear = AppKit.NSButton.alloc().initWithFrame_(
                NSMakeRect(134, 8, 90, 28))
            clear.setTitle_("Clear")
            clear.setBezelStyle_(AppKit.NSBezelStyleRounded)
            clear.setTarget_(self)
            clear.setAction_("clearHistory:")
            view.addSubview_(clear)

            count_lbl = self._label("", 236, 12, cw - 252)
            view.addSubview_(count_lbl)
            self._history_count = count_lbl

            scroll = AppKit.NSScrollView.alloc().initWithFrame_(
                NSMakeRect(12, 46, cw - 24, ch - 58))
            scroll.setHasVerticalScroller_(True)
            scroll.setBorderType_(AppKit.NSBezelBorder)
            table = AppKit.NSTableView.alloc().initWithFrame_(
                NSMakeRect(0, 0, cw - 24, ch - 58))
            col = AppKit.NSTableColumn.alloc().initWithIdentifier_("event")
            col.setWidth_(cw - 44)
            col.setTitle_("Event")
            col.setEditable_(False)
            table.addTableColumn_(col)
            table.setDataSource_(self)
            scroll.setDocumentView_(table)
            view.addSubview_(scroll)
            self._history_table = table

            self._reload_history()
            return item

        @objc.python_method
        def _fmt_event(self, row):
            ts = row["ts"].replace("T", " ")
            name = row["label"] or row["kind"]
            return f"{ts}  {name} · {row['action']}"

        @objc.python_method
        def _reload_history(self):
            # All events, newest first (history.all() is ascending by id).
            self._history_rows = [self._fmt_event(r)
                                  for r in reversed(self._app.history.all())]
            self._history_table.reloadData()
            total = len(self._history_rows)
            self._history_count.setStringValue_(
                f"{total} events" if total else "no events yet")

        def exportHistory_(self, sender):
            self._app.export_history(None)

        def clearHistory_(self, sender):
            self._app.clear_history(None)  # confirms, clears, rebuilds menu
            self._reload_history()

        # -- alarm tab actions (edit list in place, persist immediately) --
        def addAlarm_(self, sender):
            new = edit_alarm_dialog(self._app, None)
            if new:
                self._app.add_alarm(new)
            self._table.reloadData()

        def editAlarm_(self, sender):
            row = self._table.selectedRow()
            if row < 0:
                return
            updated = edit_alarm_dialog(self._app, self._app.alarms[row])
            if updated:
                self._app.update_alarm(updated)
            self._table.reloadData()

        def deleteAlarm_(self, sender):
            row = self._table.selectedRow()
            if row < 0:
                return
            alarm = self._app.alarms[row]
            if widgets.confirm("Delete this alarm?", ok="Delete"):
                self._app.delete_alarm(alarm.id)
            self._table.reloadData()

        def previewSound_(self, sender):
            title = sender.titleOfSelectedItem()
            if title:
                self._app.cue_player.play(title, loop=False)

        # -- About tab ----------------------------------------------------
        @objc.python_method
        def _link_button(self, label, left_icon_name, action, template_icon=False):
            """A rounded button: [left icon] label [external-link icon].

            Sized to its content (origin set by the caller) so the external-link
            glyph lands at the button's right edge. ``template_icon`` renders a
            monochrome left icon (e.g. the GitHub mark) so it adapts to light/dark.
            """
            btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 30))
            btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            btn.setTarget_(self)
            btn.setAction_(action)

            icon = self._app._asset(left_icon_name) if left_icon_name else None
            if icon:
                li = AppKit.NSImage.alloc().initWithContentsOfFile_(icon)
                if li is not None:
                    li.setSize_((16, 16))
                    li.setTemplate_(template_icon)
                    btn.setImage_(li)
                    btn.setImagePosition_(AppKit.NSImageLeft)
                    btn.setImageScaling_(AppKit.NSImageScaleProportionallyDown)

            title = AppKit.NSMutableAttributedString.alloc().initWithString_(label + "  ")
            ext = self._app._asset("extlink.png")
            if ext:
                ei = AppKit.NSImage.alloc().initWithContentsOfFile_(ext)
                if ei is not None:
                    ei.setSize_((12, 12))
                    att = AppKit.NSTextAttachment.alloc().init()
                    att.setImage_(ei)
                    att.setBounds_(NSMakeRect(0, -1.5, 12, 12))
                    title.appendAttributedString_(
                        AppKit.NSAttributedString.attributedStringWithAttachment_(att))
            btn.setAttributedTitle_(title)

            btn.sizeToFit()
            f = btn.frame()
            btn.setFrameSize_((f.size.width + 14, 30))  # a little breathing room
            return btn

        @objc.python_method
        def _about_tab(self, cw, ch):
            from .. import __version__
            item, view = self._tab_view("about", "About", cw, ch)

            iv = AppKit.NSImageView.alloc().initWithFrame_(
                NSMakeRect(16, ch - 84, 72, 72))
            about = self._app._asset("about.png")
            img = (AppKit.NSImage.alloc().initWithContentsOfFile_(about) if about
                   else AppKit.NSApplication.sharedApplication().applicationIconImage())
            if img is not None:
                iv.setImage_(img)
            iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
            view.addSubview_(iv)

            title = self._label(f"Tomatick {__version__}", 100, ch - 48, cw - 116)
            try:
                title.setFont_(AppKit.NSFont.boldSystemFontOfSize_(18))
            except Exception:  # pragma: no cover
                pass
            view.addSubview_(title)

            body = AppKit.NSTextField.alloc().initWithFrame_(
                NSMakeRect(100, ch - 84, cw - 116, 32))
            body.setBezeled_(False)
            body.setDrawsBackground_(False)
            body.setEditable_(False)
            body.setSelectable_(True)
            body.setStringValue_(
                "A macOS menu bar timer, stopwatch, alarm and pomodoro.")
            try:
                body.cell().setWraps_(True)
            except Exception:  # pragma: no cover
                pass
            view.addSubview_(body)

            guide = self._link_button("Quick Start Guide", "mb_red.png", "openGuide:")
            guide.setFrameOrigin_((16, ch - 150))
            view.addSubview_(guide)

            repo = self._link_button("GitHub Repo", "octocat.png", "openRepo:",
                                     template_icon=True)
            repo.setFrameOrigin_((16, ch - 186))
            view.addSubview_(repo)

            bmc_path = self._app._asset("bmc.png")
            if bmc_path:
                bi = AppKit.NSImage.alloc().initWithContentsOfFile_(bmc_path)
                if bi is not None and bi.size().height:
                    h = 40.0
                    w = h * bi.size().width / bi.size().height
                    bi.setSize_((w, h))
                    bmc = AppKit.NSButton.alloc().initWithFrame_(
                        NSMakeRect(16, ch - 244, w, h))
                    bmc.setBordered_(False)
                    bmc.setImage_(bi)
                    bmc.setImagePosition_(AppKit.NSImageOnly)
                    bmc.setTarget_(self)
                    bmc.setAction_("openBMC:")
                    view.addSubview_(bmc)
            return item

        def openGuide_(self, sender):
            self._app.open_help()

        def openRepo_(self, sender):
            self._app.open_repo()

        def openBMC_(self, sender):
            self._app.open_bmc()

        # -- Save / Cancel / close ---------------------------------------
        def save_(self, sender):
            settings = self._app.settings
            pomo = settings.pomodoro
            for key, field in self._pomo_fields.items():
                pomo[key] = self._read_int(field, pomo[key])
            pomo["auto_start_next"] = (
                self._auto.state() == AppKit.NSControlStateValueOn)

            title = self._sound.titleOfSelectedItem()
            if title:
                settings.data["default_sound"] = title
            settings.data["icon_theme"] = (
                self._mb_theme.titleOfSelectedItem() or "Red").lower()
            settings.data["snooze_minutes"] = self._read_int(
                self._snooze, settings.snooze_minutes)

            # Focus / DND
            settings.data["focus_shortcut_on"] = self._focus_on.stringValue().strip()
            settings.data["focus_shortcut_off"] = self._focus_off.stringValue().strip()
            settings.data["focus_during_work"] = (
                self._focus_during.state() == AppKit.NSControlStateValueOn)

            # Global hotkey
            sel = self._hk_action.titleOfSelectedItem()
            settings.data["hotkey_action"] = next(
                (aid for aid, lbl in hotkey.HOTKEY_ACTIONS if lbl == sel), "none")
            ksel = self._hk_key.titleOfSelectedItem()
            settings.data["hotkey_key"] = "" if ksel in (None, "(none)") else ksel

            want_login = self._launch.state() == AppKit.NSControlStateValueOn
            if want_login != settings.launch_at_login:
                try:
                    self._app.apply_launch_at_login(want_login)
                except Exception as exc:  # pragma: no cover
                    widgets.confirm(f"Couldn't update launch-at-login: {exc}")

            settings.save()
            self._app._configure_hotkey()
            self._app._load_icon_frames()  # apply menu-bar theme change
            self._app._sync_alarm_animation()  # resync if theme changed mid-alarm
            self._app.rebuild_menu()
            self._app._update_title()
            self._window.close()

        def cancel_(self, sender):
            self._window.close()

        def windowWillClose_(self, notification):
            AppKit.NSApp.stopModal()

    _SETTINGS_CONTROLLER = _SettingsController
    return _SETTINGS_CONTROLLER
