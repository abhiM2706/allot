"""Calendar adapter. Fixture version reads calendar.json. A Google Calendar version would call
events.list for the rep's primary calendar with timeMin/timeMax around the receipt time.
Only the rep's own calendar is read, and only around the transaction time."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import FIXTURES_DIR


@dataclass
class CalendarEvent:
    id: str
    rep_id: str
    title: str
    start: datetime
    end: datetime
    location: str
    attendees: list[str]

    @property
    def external_domains(self) -> set[str]:
        return {a.split("@")[1] for a in self.attendees if "@" in a and not a.endswith("acme.example")}


class Calendar:
    def __init__(self, path=FIXTURES_DIR / "calendar.json"):
        self.events = [
            CalendarEvent(e["id"], e["rep_id"], e["title"], datetime.fromisoformat(e["start"]),
                          datetime.fromisoformat(e["end"]), e.get("location", ""), e["attendees"])
            for e in json.loads(path.read_text())
        ]

    def around(self, rep_id: str, when: datetime, window_hours: float = 3) -> list[CalendarEvent]:
        w = timedelta(hours=window_hours)
        out = []
        for e in self.events:
            if e.rep_id != rep_id:
                continue
            if e.start - w <= when <= e.end + w:
                out.append(e)
        # closest first
        out.sort(key=lambda e: abs((e.start - when).total_seconds()))
        return out
