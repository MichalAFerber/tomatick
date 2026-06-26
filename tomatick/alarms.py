"""Alarm model and scheduling.

An alarm is either *one-shot* (a specific date + time, fires once) or
*recurring* (a time of day on selected weekdays). Scheduling is pure datetime
arithmetic so it is fully unit testable. Weekdays follow Python's convention:
Monday = 0 ... Sunday = 6 (``datetime.weekday()``).
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

ONE_SHOT = "one_shot"
RECURRING = "recurring"

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_alarm_id_counter = itertools.count(1)


def _parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


class Alarm:
    """A single alarm definition plus its computed next firing time."""

    def __init__(
        self,
        label: str = "",
        time_str: str = "08:00",
        kind: str = RECURRING,
        date_str: Optional[str] = None,
        days_of_week: Optional[List[int]] = None,
        enabled: bool = True,
        sound: Optional[str] = None,
        id: Optional[int] = None,
    ):
        self.id = id if id is not None else next(_alarm_id_counter)
        self.label = label
        self.time_str = time_str  # "HH:MM"
        self.kind = kind
        self.date_str = date_str  # "YYYY-MM-DD" for one-shot
        self.days_of_week = sorted(set(days_of_week or []))
        self.enabled = enabled
        self.sound = sound
        self.next_fire: Optional[datetime] = None

    # -- (de)serialization -------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "label": self.label,
            "time_str": self.time_str,
            "kind": self.kind,
            "date_str": self.date_str,
            "days_of_week": self.days_of_week,
            "enabled": self.enabled,
            "sound": self.sound,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Alarm":
        return cls(
            id=d.get("id"),
            label=d.get("label", ""),
            time_str=d.get("time_str", "08:00"),
            kind=d.get("kind", RECURRING),
            date_str=d.get("date_str"),
            days_of_week=d.get("days_of_week", []),
            enabled=d.get("enabled", True),
            sound=d.get("sound"),
        )

    # -- scheduling --------------------------------------------------------
    def compute_next_fire(self, now: Optional[datetime] = None) -> Optional[datetime]:
        """Return the next datetime this alarm should fire at, or None.

        For a one-shot alarm in the past, returns that past datetime (the app
        treats ``next_fire <= now`` as "fire now", then disables it). A
        recurring alarm with no selected days returns None.
        """
        now = now or datetime.now()
        if not self.enabled:
            self.next_fire = None
            return None

        t = _parse_hhmm(self.time_str)

        if self.kind == ONE_SHOT:
            if not self.date_str:
                self.next_fire = None
                return None
            d = date.fromisoformat(self.date_str)
            self.next_fire = datetime.combine(d, t)
            return self.next_fire

        # Recurring: scan forward up to 8 days for the next matching weekday.
        if not self.days_of_week:
            self.next_fire = None
            return None
        for offset in range(0, 8):
            candidate_date = (now + timedelta(days=offset)).date()
            if candidate_date.weekday() in self.days_of_week:
                candidate = datetime.combine(candidate_date, t)
                if candidate > now:
                    self.next_fire = candidate
                    return candidate
        self.next_fire = None
        return None

    def mark_fired(self, now: Optional[datetime] = None) -> None:
        """Update state after firing: disable one-shots, reschedule recurring."""
        now = now or datetime.now()
        if self.kind == ONE_SHOT:
            self.enabled = False
            self.next_fire = None
        else:
            # Recompute from just after the fire time to avoid immediate re-fire.
            self.compute_next_fire(now + timedelta(seconds=1))

    # -- display -----------------------------------------------------------
    def describe(self) -> str:
        """Human-readable schedule summary, e.g. 'Weekdays 09:00' or 'Once 2026-06-27 14:30'."""
        if self.kind == ONE_SHOT:
            return f"Once {self.date_str or '?'} {self.time_str}"
        if not self.days_of_week:
            return f"(no days) {self.time_str}"
        if self.days_of_week == [0, 1, 2, 3, 4]:
            days = "Weekdays"
        elif self.days_of_week == [5, 6]:
            days = "Weekends"
        elif len(self.days_of_week) == 7:
            days = "Daily"
        else:
            days = ",".join(WEEKDAY_NAMES[d] for d in self.days_of_week)
        return f"{days} {self.time_str}"

    def menu_text(self) -> str:
        name = self.label or "Alarm"
        state = "" if self.enabled else "  (off)"
        return f"🔔 {name} · {self.describe()}{state}"


def load_alarms(settings_alarms: List[Dict]) -> List[Alarm]:
    """Build Alarm objects from serialized settings and compute their schedules."""
    alarms = [Alarm.from_dict(d) for d in settings_alarms]
    for a in alarms:
        a.compute_next_fire()
    return alarms


def due_alarms(alarms: List[Alarm], now: Optional[datetime] = None) -> List[Alarm]:
    """Return the alarms whose next_fire has arrived (<= now)."""
    now = now or datetime.now()
    out = []
    for a in alarms:
        if a.enabled and a.next_fire is not None and a.next_fire <= now:
            out.append(a)
    return out
