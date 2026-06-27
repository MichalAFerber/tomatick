"""Dialog to add/edit a quick-start timer preset.

Returns a ``{"label", "seconds"}`` dict, or None if cancelled. Used by the
Presets tab in the settings window.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..sessions import format_clock, parse_duration
from . import widgets

if TYPE_CHECKING:  # pragma: no cover
    from ..app import TomatickApp


def edit_preset_dialog(app: "TomatickApp", existing: Optional[dict]) -> Optional[dict]:
    label = widgets.ask_text("Preset name:", title="Preset",
                             default=existing["label"] if existing else "")
    if label is None:
        return None

    default_dur = format_clock(existing["seconds"]) if existing else ""
    dur = widgets.ask_text("Duration (e.g. 25m, 1h30m, 90s):", title="Preset",
                           default=default_dur)
    if dur is None:
        return None
    try:
        seconds = parse_duration(dur)
    except ValueError:
        widgets.confirm(f"Couldn't understand '{dur}'.")
        return None
    if seconds <= 0:
        return None
    return {"label": label.strip(), "seconds": seconds}
