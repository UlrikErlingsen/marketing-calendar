"""Lead times: work backwards from a moment to planning milestones.

Offsets are whole weeks before the moment's first day. They are planning conventions, not research
findings — the defaults are a starting point and are meant to be edited.
"""

from __future__ import annotations

import math
import numbers
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Mapping

from .errors import PlanProblem

MILESTONES: tuple[tuple[str, str], ...] = (
    ("concept", "Concept & brief"),
    ("creative", "Creative production"),
    ("media", "Media booking"),
    ("live", "Campaign live"),
)

# Weeks before the moment starts. Longer for categories whose partners plan earlier: grocery chains lock
# campaign slots months ahead (food, alcohol-free), travel buyers book early, fashion buys seasons ahead.
DEFAULT_LEAD_TIMES: dict[str, dict[str, int]] = {
    "retail": {"concept": 10, "creative": 6, "media": 4, "live": 1},
    "food": {"concept": 16, "creative": 10, "media": 6, "live": 1},
    "fashion": {"concept": 16, "creative": 8, "media": 4, "live": 1},
    "travel": {"concept": 20, "creative": 10, "media": 6, "live": 3},
    "b2b": {"concept": 12, "creative": 8, "media": 4, "live": 2},
    "alcohol_free": {"concept": 16, "creative": 10, "media": 6, "live": 1},
    "kids": {"concept": 12, "creative": 6, "media": 4, "live": 1},
}


@dataclass(frozen=True)
class Milestone:
    key: str
    label: str
    weeks_before: int
    due: date
    moved_from: date | None = None  # set when the raw date fell on a weekend or public holiday

    def status(self, today: date) -> str:
        days = (self.due - today).days
        if days < 0:
            return "overdue"
        if days <= 14:
            return "due soon"
        return "on track"


def validate_lead_times(table: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, int]]:
    """Check a lead-time table: whole, non-negative weeks, in a sensible order. Returns a clean copy."""
    clean: dict[str, dict[str, int]] = {}
    for category, offsets in table.items():
        row: dict[str, int] = {}
        for key, _label in MILESTONES:
            value = offsets.get(key)
            whole = isinstance(value, numbers.Real) and not isinstance(value, bool) and math.isfinite(value)
            if not whole or value != int(value):
                raise PlanProblem(f"{category}: '{key}' lead time must be a whole number of weeks.")
            weeks = int(value)
            if not 0 <= weeks <= 52:
                raise PlanProblem(f"{category}: '{key}' lead time must be between 0 and 52 weeks.")
            row[key] = weeks
        order = [row[key] for key, _label in MILESTONES]
        if order != sorted(order, reverse=True):
            raise PlanProblem(
                f"{category}: milestones must run in order — concept ≥ creative ≥ media booking ≥ live (in weeks)."
            )
        clean[str(category)] = row
    return clean


def previous_working_day(day: date, holidays: Iterable[date]) -> date:
    """Move a date back to the nearest weekday that is not a public holiday."""
    closed = set(holidays)
    while day.weekday() >= 5 or day in closed:
        day -= timedelta(days=1)
    return day


def plan_back(
    moment_start: date,
    offsets: Mapping[str, int],
    holidays: Iterable[date] = (),
    *,
    working_days: bool = True,
) -> list[Milestone]:
    """Milestones for a moment: each is ``weeks`` before ``moment_start``, optionally moved to a working day.

    ``holidays`` should cover the years the milestones can fall in (they can precede the moment's year).
    """
    closed = set(holidays)
    milestones = []
    for key, label in MILESTONES:
        weeks = int(offsets[key])
        raw = moment_start - timedelta(weeks=weeks)
        due = previous_working_day(raw, closed) if working_days else raw
        milestones.append(Milestone(key, label, weeks, due, raw if due != raw else None))
    return milestones
