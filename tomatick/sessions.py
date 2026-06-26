"""Session models: Timer, Stopwatch, Pomodoro.

All timekeeping is driven by an external 1-second tick (see app.TomatickApp),
so these classes contain no timers/threads of their own and are fully unit
testable. ``tick()`` advances a session by ``seconds`` (default 1) and returns
a list of *events* describing anything noteworthy that happened, which the app
layer translates into history rows, notifications and sounds.
"""

from __future__ import annotations

import itertools
import re
from datetime import datetime
from typing import Dict, List, Optional

# Session states
RUNNING = "running"
PAUSED = "paused"
DONE = "done"

# Pomodoro phases
WORK = "work"
SHORT_BREAK = "short_break"
LONG_BREAK = "long_break"

_id_counter = itertools.count(1)


def _next_id() -> int:
    return next(_id_counter)


def parse_duration(text: str) -> int:
    """Parse a natural-language duration into seconds.

    Accepts forms like ``25m``, ``1h30m``, ``90s``, ``1h``, ``45`` (bare number
    means minutes), and ``mm:ss`` / ``hh:mm:ss``. Raises ValueError on garbage.
    """
    text = text.strip().lower()
    if not text:
        raise ValueError("empty duration")

    # Colon form: mm:ss or hh:mm:ss
    if ":" in text:
        parts = [int(p) for p in text.split(":")]
        if len(parts) == 2:
            m, s = parts
            return m * 60 + s
        if len(parts) == 3:
            h, m, s = parts
            return h * 3600 + m * 60 + s
        raise ValueError(f"bad time format: {text!r}")

    # Bare integer => minutes
    if re.fullmatch(r"\d+", text):
        return int(text) * 60

    # Unit form: any combination of <num>h <num>m <num>s
    matches = re.findall(r"(\d+)\s*([hms])", text)
    if not matches:
        raise ValueError(f"cannot parse duration: {text!r}")
    total = 0
    for value, unit in matches:
        n = int(value)
        total += n * {"h": 3600, "m": 60, "s": 1}[unit]
    return total


def format_clock(seconds: int) -> str:
    """Format seconds as M:SS, or H:MM:SS once an hour is reached."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class Session:
    """Base class for a tracked, tickable session."""

    kind = "session"
    icon = "⏱"

    def __init__(self, label: Optional[str] = None):
        self.id = _next_id()
        self.label = label or ""
        self.state = RUNNING
        self.started_at = datetime.now()
        self.pinned = False

    # -- lifecycle ---------------------------------------------------------
    def pause(self) -> None:
        if self.state == RUNNING:
            self.state = PAUSED

    def resume(self) -> None:
        if self.state == PAUSED:
            self.state = RUNNING

    def toggle_pause(self) -> str:
        """Flip running/paused; returns the action name for history."""
        if self.state == RUNNING:
            self.pause()
            return "paused"
        if self.state == PAUSED:
            self.resume()
            return "resumed"
        return ""

    def reset(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def tick(self, seconds: int = 1) -> List[Dict]:  # pragma: no cover - overridden
        raise NotImplementedError

    # -- display -----------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.state in (RUNNING, PAUSED)

    @property
    def is_countdown(self) -> bool:
        """Whether this session contributes a live countdown to the title."""
        return True

    def title_text(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def menu_text(self) -> str:
        name = self.label or self.kind.capitalize()
        suffix = " (paused)" if self.state == PAUSED else ""
        return f"{self.icon} {name}  {self.title_text()}{suffix}"


class Timer(Session):
    """Counts down from ``duration`` seconds to zero."""

    kind = "timer"
    icon = "⏱"

    def __init__(self, duration: int, label: Optional[str] = None):
        super().__init__(label)
        self.duration = int(duration)
        self.remaining = int(duration)

    def reset(self) -> None:
        self.remaining = self.duration
        self.state = RUNNING

    def tick(self, seconds: int = 1) -> List[Dict]:
        if self.state != RUNNING:
            return []
        self.remaining = max(0, self.remaining - seconds)
        if self.remaining == 0:
            self.state = DONE
            return [{"action": "completed", "kind": self.kind, "label": self.label,
                     "duration_s": self.duration}]
        return []

    def title_text(self) -> str:
        return format_clock(self.remaining)


class Stopwatch(Session):
    """Counts up indefinitely."""

    kind = "stopwatch"
    icon = "⏲"

    def __init__(self, label: Optional[str] = None):
        super().__init__(label)
        self.elapsed = 0
        self.laps: List[int] = []

    def reset(self) -> None:
        self.elapsed = 0
        self.laps = []
        self.state = RUNNING

    def lap(self) -> int:
        self.laps.append(self.elapsed)
        return self.elapsed

    def tick(self, seconds: int = 1) -> List[Dict]:
        if self.state != RUNNING:
            return []
        self.elapsed += seconds
        return []

    def title_text(self) -> str:
        return format_clock(self.elapsed)


class Pomodoro(Session):
    """Cycles through work / short break / long break phases automatically."""

    kind = "pomodoro"

    def __init__(self, config: Dict, label: Optional[str] = None):
        super().__init__(label)
        self.work_s = int(config["work_minutes"]) * 60
        self.short_s = int(config["short_break_minutes"]) * 60
        self.long_s = int(config["long_break_minutes"]) * 60
        self.cycles_before_long = int(config["cycles_before_long_break"])
        self.auto_start_next = bool(config.get("auto_start_next", True))

        self.phase = WORK
        self.completed_work_cycles = 0  # work sessions finished so far
        self.remaining = self.work_s

    # -- phase helpers -----------------------------------------------------
    @property
    def icon(self) -> str:  # type: ignore[override]
        return "🍅" if self.phase == WORK else "☕"

    def _phase_duration(self, phase: str) -> int:
        return {WORK: self.work_s, SHORT_BREAK: self.short_s, LONG_BREAK: self.long_s}[phase]

    def _next_phase(self) -> str:
        """Determine the phase that follows the current one."""
        if self.phase == WORK:
            # A long break after every Nth completed work cycle.
            if self.completed_work_cycles % self.cycles_before_long == 0:
                return LONG_BREAK
            return SHORT_BREAK
        return WORK

    def _enter_phase(self, phase: str) -> None:
        self.phase = phase
        self.remaining = self._phase_duration(phase)
        self.state = RUNNING if self.auto_start_next else PAUSED

    def skip_phase(self) -> List[Dict]:
        """Force-advance to the next phase (used by the Skip menu action)."""
        return self._advance(skipped=True)

    def _advance(self, skipped: bool = False) -> List[Dict]:
        finishing = self.phase
        if finishing == WORK:
            self.completed_work_cycles += 1
        nxt = self._next_phase()
        self._enter_phase(nxt)
        return [{
            "action": "phase_change",
            "kind": self.kind,
            "label": self.label,
            "details": {"from": finishing, "to": nxt, "skipped": skipped,
                        "completed_work_cycles": self.completed_work_cycles},
        }]

    def reset(self) -> None:
        self.phase = WORK
        self.completed_work_cycles = 0
        self.remaining = self.work_s
        self.state = RUNNING

    def tick(self, seconds: int = 1) -> List[Dict]:
        if self.state != RUNNING:
            return []
        self.remaining = max(0, self.remaining - seconds)
        if self.remaining == 0:
            return self._advance(skipped=False)
        return []

    def title_text(self) -> str:
        return format_clock(self.remaining)

    def menu_text(self) -> str:
        name = self.label or "Pomodoro"
        phase_label = {WORK: "work", SHORT_BREAK: "break", LONG_BREAK: "long break"}[self.phase]
        suffix = " (paused)" if self.state == PAUSED else ""
        return f"{self.icon} {name} · {phase_label}  {self.title_text()}{suffix}"
