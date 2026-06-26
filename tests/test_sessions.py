"""Logic tests that run on any platform (no rumps/AppKit imports)."""

import os
import tempfile
from datetime import datetime

import pytest

from tomatick.sessions import (DONE, PAUSED, RUNNING, Pomodoro, Stopwatch, Timer,
                               WORK, SHORT_BREAK, LONG_BREAK, format_clock,
                               parse_duration)

POMO_CONFIG = {
    "work_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "cycles_before_long_break": 4,
    "auto_start_next": True,
}


# -- parse_duration ---------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("25m", 1500),
    ("1h30m", 5400),
    ("90s", 90),
    ("1h", 3600),
    ("45", 2700),          # bare number = minutes
    ("2:30", 150),         # mm:ss
    ("1:00:00", 3600),     # hh:mm:ss
    ("1h 30m 15s", 5415),
])
def test_parse_duration_ok(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "h", "1x"])
def test_parse_duration_bad(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_format_clock():
    assert format_clock(5) == "0:05"
    assert format_clock(75) == "1:15"
    assert format_clock(3661) == "1:01:01"
    assert format_clock(-5) == "0:00"


# -- Timer ------------------------------------------------------------------
def test_timer_counts_down_and_completes():
    t = Timer(3)
    assert t.tick() == []
    assert t.remaining == 2
    assert t.tick() == []
    events = t.tick()  # hits zero
    assert t.remaining == 0
    assert t.state == DONE
    assert events and events[0]["action"] == "completed"
    assert events[0]["duration_s"] == 3


def test_timer_pause_blocks_tick():
    t = Timer(10)
    t.pause()
    assert t.state == PAUSED
    t.tick()
    assert t.remaining == 10  # unchanged while paused
    t.resume()
    t.tick()
    assert t.remaining == 9


def test_timer_reset():
    t = Timer(10)
    for _ in range(5):
        t.tick()
    assert t.remaining == 5
    t.reset()
    assert t.remaining == 10
    assert t.state == RUNNING


# -- Stopwatch --------------------------------------------------------------
def test_stopwatch_counts_up_and_laps():
    s = Stopwatch()
    for _ in range(5):
        s.tick()
    assert s.elapsed == 5
    assert s.lap() == 5
    s.tick()
    assert s.lap() == 6
    assert s.laps == [5, 6]


# -- Pomodoro ---------------------------------------------------------------
def _drain(session, seconds):
    """Tick ``seconds`` times, collecting all emitted events."""
    out = []
    for _ in range(seconds):
        out.extend(session.tick())
    return out


def test_pomodoro_work_then_short_break():
    p = Pomodoro(POMO_CONFIG)
    assert p.phase == WORK
    events = _drain(p, 25 * 60)
    assert any(e["action"] == "phase_change" for e in events)
    assert p.phase == SHORT_BREAK
    assert p.completed_work_cycles == 1


def test_pomodoro_long_break_after_four_cycles():
    p = Pomodoro(POMO_CONFIG)
    phases_seen = [p.phase]
    # Run long enough to cross several phases; record transitions.
    for _ in range(4):
        # finish current work phase
        _drain(p, p.remaining)
        phases_seen.append(p.phase)
        # finish the break phase
        _drain(p, p.remaining)
        phases_seen.append(p.phase)
    # The break after the 4th work cycle must be the long break.
    assert LONG_BREAK in phases_seen


def test_pomodoro_skip_phase():
    p = Pomodoro(POMO_CONFIG)
    events = p.skip_phase()
    assert events[0]["action"] == "phase_change"
    assert events[0]["details"]["skipped"] is True
    assert p.phase == SHORT_BREAK


def test_pomodoro_no_autostart_pauses_after_phase():
    cfg = dict(POMO_CONFIG, auto_start_next=False)
    p = Pomodoro(cfg)
    _drain(p, p.remaining)
    assert p.phase == SHORT_BREAK
    assert p.state == PAUSED
