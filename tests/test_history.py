"""History store tests (SQLite, no macOS deps)."""

import json
from datetime import datetime

import pytest

from tomatick.history import History


@pytest.fixture
def hist(tmp_path):
    h = History(path=tmp_path / "history.db")
    yield h
    h.close()


def test_log_and_recent(hist):
    hist.log_event("timer", "started", label="tea", duration_s=300,
                   ts=datetime(2026, 6, 26, 10, 0))
    hist.log_event("timer", "completed", label="tea",
                   ts=datetime(2026, 6, 26, 10, 5))
    rows = hist.recent(10)
    assert len(rows) == 2
    # recent() is newest-first
    assert rows[0]["action"] == "completed"
    assert rows[1]["label"] == "tea"
    assert rows[1]["duration_s"] == 300


def test_details_json(hist):
    hist.log_event("pomodoro", "phase_change", details={"from": "work", "to": "break"})
    row = hist.recent(1)[0]
    assert json.loads(row["details_json"]) == {"from": "work", "to": "break"}


def test_count_and_clear(hist):
    for i in range(3):
        hist.log_event("stopwatch", "started")
    assert hist.count() == 3
    hist.clear()
    assert hist.count() == 0


def test_export_csv_and_json(hist, tmp_path):
    hist.log_event("timer", "started", label="x", duration_s=60,
                   ts=datetime(2026, 6, 26, 9, 0))
    csv_path = hist.export_csv(tmp_path / "out.csv")
    json_path = hist.export_json(tmp_path / "out.json")
    assert csv_path.exists()
    assert "started" in csv_path.read_text()
    data = json.loads(json_path.read_text())
    assert data[0]["label"] == "x"
    assert data[0]["duration_s"] == 60
