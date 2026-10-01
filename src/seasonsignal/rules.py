"""Date rules: turn a declarative rule from the moments library into a date for a given year.

Every date in SeasonSignal is computed from a rule; nothing is hard-coded per year.

Supported rules (all accept an optional ``offset`` in days, and an optional ``year_offset`` for ranges that
cross New Year, e.g. a school Christmas break ending 3 January of the following year):

- ``fixed``: ``month`` + ``day``.
- ``easter``: Western (Gregorian) Easter Sunday, as used by the Church of Norway and helligdagsfredloven.
- ``nth_weekday``: the ``n``-th ``weekday`` of ``month``; negative ``n`` counts from the end of the month.
- ``weekday_on_or_after``: the first ``weekday`` on or after ``month``/``day``.
- ``iso_week``: ``weekday`` of ISO-8601 week ``week`` (Norway numbers weeks by ISO 8601).
- ``relative``: the start date of another moment (``to``), e.g. Cyber Monday = Black Friday + 3.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable, Mapping

from dateutil.easter import EASTER_WESTERN, easter

from . import MAX_YEAR, MIN_YEAR
from .errors import PlanProblem

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
RULES = ("fixed", "easter", "nth_weekday", "weekday_on_or_after", "iso_week", "relative")

Resolver = Callable[[str, int], date]


def check_year(year: int) -> int:
    if not isinstance(year, int) or not MIN_YEAR <= year <= MAX_YEAR:
        raise PlanProblem(f"Choose a year between {MIN_YEAR} and {MAX_YEAR} (got {year!r}).")
    return year


def easter_sunday(year: int) -> date:
    return easter(year, EASTER_WESTERN)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th weekday (0=Monday) of a month; n=-1 is the last one."""
    if n == 0:
        raise PlanProblem("nth_weekday needs n >= 1 or n <= -1.")
    if n > 0:
        first = date(year, month, 1)
        result = first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    else:
        nxt = date(year + (month == 12), month % 12 + 1, 1)
        last = nxt - timedelta(days=1)
        result = last - timedelta(days=(last.weekday() - weekday) % 7 + 7 * (-n - 1))
    if result.month != month:
        raise PlanProblem(f"There is no occurrence number {n} of that weekday in {year}-{month:02d}.")
    return result


def weekday_on_or_after(day: date, weekday: int) -> date:
    return day + timedelta(days=(weekday - day.weekday()) % 7)


def iso_week_day(year: int, week: int, weekday: int) -> date:
    try:
        return date.fromisocalendar(year, week, weekday + 1)
    except ValueError as exc:
        raise PlanProblem(f"ISO week {week} does not exist in {year}.") from exc


def _weekday(spec: Mapping[str, Any]) -> int:
    name = str(spec.get("weekday", "")).lower()
    full_names = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    name = name[:3] if name in full_names else name
    if name not in WEEKDAYS:
        raise PlanProblem(f"Unknown weekday {spec.get('weekday')!r}; use one of {', '.join(WEEKDAYS)}.")
    return WEEKDAYS[name]


def validate_rule(spec: Mapping[str, Any]) -> None:
    """Raise PlanProblem if a rule is structurally invalid (does not evaluate it)."""
    if not isinstance(spec, Mapping) or spec.get("rule") not in RULES:
        raise PlanProblem(f"Each date needs a 'rule' from {', '.join(RULES)}; got {spec!r}.")
    required = {
        "fixed": ("month", "day"),
        "easter": (),
        "nth_weekday": ("month", "weekday", "n"),
        "weekday_on_or_after": ("month", "day", "weekday"),
        "iso_week": ("week", "weekday"),
        "relative": ("to",),
    }[spec["rule"]]
    missing = [key for key in required if key not in spec]
    if missing:
        raise PlanProblem(f"Rule {spec['rule']!r} is missing {', '.join(missing)}.")
    if "weekday" in required:
        _weekday(spec)
    if not isinstance(spec.get("offset", 0), int) or not isinstance(spec.get("year_offset", 0), int):
        raise PlanProblem("A rule offset must be a whole number of days (and year_offset a whole number of years).")


def evaluate(spec: Mapping[str, Any], year: int, resolve: Resolver | None = None) -> date:
    """Evaluate a rule for a year. ``resolve`` looks up another moment's start for ``relative`` rules."""
    validate_rule(spec)
    rule = spec["rule"]
    year += int(spec.get("year_offset", 0))
    if rule == "fixed":
        base = date(year, int(spec["month"]), int(spec["day"]))
    elif rule == "easter":
        base = easter_sunday(year)
    elif rule == "nth_weekday":
        base = nth_weekday(year, int(spec["month"]), _weekday(spec), int(spec["n"]))
    elif rule == "weekday_on_or_after":
        base = weekday_on_or_after(date(year, int(spec["month"]), int(spec["day"])), _weekday(spec))
    elif rule == "iso_week":
        base = iso_week_day(year, int(spec["week"]), _weekday(spec))
    else:
        if resolve is None:
            raise PlanProblem("A 'relative' rule needs the moments library to resolve it.")
        base = resolve(str(spec["to"]), year)
    return base + timedelta(days=int(spec.get("offset", 0)))


def describe(spec: Mapping[str, Any]) -> str:
    """A short human-readable description of a rule, for the sources table."""
    rule = spec.get("rule")
    offset = int(spec.get("offset", 0))
    suffix = "" if not offset else f" {'+' if offset > 0 else '−'} {abs(offset)} d"
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", -1: "last", -2: "2nd-last"}
    if rule == "fixed":
        text = f"{int(spec['day'])} {months[int(spec['month'])]}"
    elif rule == "easter":
        text = "Easter Sunday"
    elif rule == "nth_weekday":
        text = f"{ordinals.get(int(spec['n']), spec['n'])} {spec['weekday']} of {months[int(spec['month'])]}"
    elif rule == "weekday_on_or_after":
        text = f"first {spec['weekday']} on/after {int(spec['day'])} {months[int(spec['month'])]}"
    elif rule == "iso_week":
        text = f"{spec['weekday']} of ISO week {int(spec['week'])}"
    elif rule == "relative":
        text = f"start of '{spec['to']}'"
    else:
        text = str(spec)
    if spec.get("year_offset"):
        suffix += f" (+{int(spec['year_offset'])} y)"
    return text + suffix
