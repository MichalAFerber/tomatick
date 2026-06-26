"""Alarm scheduling tests (pure datetime logic)."""

from datetime import datetime

from tomatick.alarms import (Alarm, ONE_SHOT, RECURRING, due_alarms,
                             load_alarms)


def test_one_shot_next_fire():
    a = Alarm(label="dentist", time_str="14:30", kind=ONE_SHOT,
              date_str="2026-06-27")
    nf = a.compute_next_fire(now=datetime(2026, 6, 26, 9, 0))
    assert nf == datetime(2026, 6, 27, 14, 30)


def test_one_shot_disables_after_fire():
    a = Alarm(kind=ONE_SHOT, time_str="08:00", date_str="2026-06-26")
    a.compute_next_fire(now=datetime(2026, 6, 26, 7, 0))
    a.mark_fired(now=datetime(2026, 6, 26, 8, 0))
    assert a.enabled is False
    assert a.next_fire is None


def test_recurring_picks_next_matching_day():
    # 2026-06-26 is a Friday (weekday 4). Alarm on Mondays (0) at 09:00.
    a = Alarm(kind=RECURRING, time_str="09:00", days_of_week=[0])
    nf = a.compute_next_fire(now=datetime(2026, 6, 26, 12, 0))
    assert nf.weekday() == 0
    assert nf.hour == 9 and nf.minute == 0
    assert nf > datetime(2026, 6, 26, 12, 0)


def test_recurring_today_if_time_not_passed():
    # Friday 08:00, alarm fires Fridays (4) at 09:00 -> today.
    a = Alarm(kind=RECURRING, time_str="09:00", days_of_week=[4])
    nf = a.compute_next_fire(now=datetime(2026, 6, 26, 8, 0))
    assert nf == datetime(2026, 6, 26, 9, 0)


def test_recurring_reschedules_after_fire():
    a = Alarm(kind=RECURRING, time_str="09:00", days_of_week=[4])
    a.compute_next_fire(now=datetime(2026, 6, 26, 8, 0))
    a.mark_fired(now=datetime(2026, 6, 26, 9, 0))
    assert a.enabled is True
    # Next occurrence is the following Friday.
    assert a.next_fire == datetime(2026, 7, 3, 9, 0)


def test_disabled_alarm_has_no_next_fire():
    a = Alarm(kind=RECURRING, time_str="09:00", days_of_week=[0], enabled=False)
    assert a.compute_next_fire(now=datetime(2026, 6, 26)) is None


def test_due_alarms():
    a = Alarm(kind=RECURRING, time_str="09:00", days_of_week=[4])
    a.compute_next_fire(now=datetime(2026, 6, 26, 8, 0))
    assert due_alarms([a], now=datetime(2026, 6, 26, 8, 59)) == []
    assert due_alarms([a], now=datetime(2026, 6, 26, 9, 0)) == [a]


def test_roundtrip_serialization():
    a = Alarm(label="x", time_str="07:15", kind=RECURRING,
              days_of_week=[1, 3], sound="Ping")
    restored = Alarm.from_dict(a.to_dict())
    assert restored.label == "x"
    assert restored.days_of_week == [1, 3]
    assert restored.sound == "Ping"


def test_describe():
    assert "Weekdays" in Alarm(kind=RECURRING, time_str="09:00",
                               days_of_week=[0, 1, 2, 3, 4]).describe()
    assert "Once" in Alarm(kind=ONE_SHOT, time_str="09:00",
                           date_str="2026-06-27").describe()
