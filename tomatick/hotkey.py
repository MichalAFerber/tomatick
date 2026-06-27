"""A single global hotkey via an NSEvent monitor.

Global key monitoring requires the app to be trusted for Accessibility
(System Settings → Privacy & Security → Accessibility). Without it the monitor
simply never fires — it degrades gracefully rather than crashing.
"""

from __future__ import annotations

try:  # AppKit only exists on macOS with PyObjC.
    import AppKit
    _HAVE_APPKIT = True
except Exception:  # pragma: no cover - non-mac
    _HAVE_APPKIT = False

# Key-combo presets offered in Settings ("" = none). Symbol order ⌃⌥⇧⌘.
HOTKEY_KEYS = ["", "⌥⌘P", "⌥⌘T", "⌥⌘K", "⌃⌥⌘P", "⌃⌥⌘T", "⌃⌥⌘K"]

# (action id, menu label) for the action dropdown.
HOTKEY_ACTIONS = [
    ("none", "(disabled)"),
    ("pomodoro", "Start Pomodoro"),
    ("timer", "Start Timer"),
    ("keepawake", "Toggle Keep Awake"),
]

_SYMBOL_TO_FLAG = {}
if _HAVE_APPKIT:
    _SYMBOL_TO_FLAG = {
        "⌘": AppKit.NSEventModifierFlagCommand,
        "⌥": AppKit.NSEventModifierFlagOption,
        "⌃": AppKit.NSEventModifierFlagControl,
        "⇧": AppKit.NSEventModifierFlagShift,
    }


def parse_combo(combo: str):
    """Return (modifier_mask, key_char_lower) for e.g. '⌥⌘P', or None."""
    if not combo or not _HAVE_APPKIT:
        return None
    mask = 0
    key = None
    for ch in combo:
        if ch in _SYMBOL_TO_FLAG:
            mask |= _SYMBOL_TO_FLAG[ch]
        else:
            key = ch.lower()
    if key is None or mask == 0:
        return None
    return mask, key


def is_trusted(prompt: bool = False) -> bool:
    """Whether we have Accessibility trust; optionally show the system prompt."""
    try:
        from ApplicationServices import (AXIsProcessTrustedWithOptions,
                                         kAXTrustedCheckOptionPrompt)
        return bool(AXIsProcessTrustedWithOptions(
            {kAXTrustedCheckOptionPrompt: bool(prompt)}))
    except Exception:  # pragma: no cover - can't check -> don't block
        return True


class HotkeyManager:
    def __init__(self, callback):
        self._callback = callback
        self._monitor = None

    def stop(self) -> None:
        if self._monitor is not None and _HAVE_APPKIT:
            AppKit.NSEvent.removeMonitor_(self._monitor)
        self._monitor = None

    def configure(self, combo: str) -> None:
        self.stop()
        parsed = parse_combo(combo)
        if not parsed or not _HAVE_APPKIT:
            return
        mask, key = parsed
        relevant = (AppKit.NSEventModifierFlagCommand
                    | AppKit.NSEventModifierFlagOption
                    | AppKit.NSEventModifierFlagControl
                    | AppKit.NSEventModifierFlagShift)
        cb = self._callback

        def handler(event):
            try:
                if (int(event.modifierFlags()) & relevant) == mask:
                    if (event.charactersIgnoringModifiers() or "").lower() == key:
                        cb()
            except Exception:  # pragma: no cover
                pass

        self._monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            AppKit.NSEventMaskKeyDown, handler)
