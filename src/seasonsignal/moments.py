"""The moments library: load the YAML, validate it, and resolve moments to dates for a year and region."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import rules
from .errors import PlanProblem

LIBRARY_DIR = Path(__file__).resolve().parent / "moments"
DEFAULT_LIBRARY = LIBRARY_DIR / "no.yaml"
BASES = ("official", "tradition", "observed", "convention")
NATIONAL = "all"


@dataclass(frozen=True)
class Variant:
    region: str
    start: Mapping[str, Any]
    end: Mapping[str, Any]
    source: str
    verified: str = ""


@dataclass(frozen=True)
class Moment:
    id: str
    name_nb: str
    name_en: str
    kind: str
    start: Mapping[str, Any]
    end: Mapping[str, Any]
    tags: tuple[str, ...]
    basis: str
    source: str
    notes: str
    varies: str = ""
    variants: tuple[Variant, ...] = ()

    @property
    def is_range(self) -> bool:
        return self.start != self.end


@dataclass(frozen=True)
class Occurrence:
    """A moment resolved to concrete dates for one year and region."""

    moment: Moment
    year: int
    region: str
    start: date
    end: date
    source: str
    regional: bool = False

    @property
    def varies_here(self) -> bool:
        # A national range for a locally set moment; a verified regional variant is exact.
        return bool(self.moment.varies) and not self.regional

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def label(self, lang: str = "nb") -> str:
        return self.moment.name_nb if lang == "nb" else self.moment.name_en


@dataclass
class Library:
    country: str
    regions: dict[str, str]
    categories: dict[str, dict[str, str]]
    kinds: dict[str, dict[str, str]]
    moments: dict[str, Moment] = field(default_factory=dict)

    def get(self, moment_id: str) -> Moment:
        try:
            return self.moments[moment_id]
        except KeyError as exc:
            raise PlanProblem(f"Unknown moment {moment_id!r}.") from exc

    def category_label(self, key: str, lang: str = "en") -> str:
        return self.categories.get(key, {}).get(lang, key)

    def resolve(self, moment_id: str, year: int, region: str = NATIONAL) -> Occurrence:
        rules.check_year(year)
        if region not in self.regions:
            raise PlanProblem(f"Unknown region {region!r}; choose one of {', '.join(self.regions)}.")
        return self._resolve(moment_id, year, region, ())

    def _resolve(self, moment_id: str, year: int, region: str, stack: tuple[str, ...]) -> Occurrence:
        if moment_id in stack:
            raise PlanProblem(f"Circular relative rule: {' → '.join((*stack, moment_id))}.")
        moment = self.get(moment_id)
        variant = next((v for v in moment.variants if v.region == region), None)
        start_rule, end_rule = (variant.start, variant.end) if variant else (moment.start, moment.end)

        def lookup(other: str, other_year: int) -> date:
            return self._resolve(other, other_year, region, (*stack, moment_id)).start

        start = rules.evaluate(start_rule, year, lookup)
        end = rules.evaluate(end_rule, year, lookup)
        if end < start:
            raise PlanProblem(f"Moment {moment_id!r} ends before it starts in {year}.")
        return Occurrence(
            moment=moment,
            year=year,
            region=region,
            start=start,
            end=end,
            source=variant.source if variant else moment.source,
            regional=variant is not None,
        )

    def occurrences(self, year: int, region: str = NATIONAL) -> list[Occurrence]:
        found = [self.resolve(moment_id, year, region) for moment_id in self.moments]
        return sorted(found, key=lambda occ: (occ.start, occ.end, occ.moment.id))

    def window(self, start: date, months: int = 12, region: str = NATIONAL) -> list[Occurrence]:
        """Occurrences overlapping [start, start + months), across a year boundary if needed."""
        stop = _add_months(start, months)
        found: list[Occurrence] = []
        for year in range(start.year - 1, stop.year + 1):  # the previous year's ranges can run into this one
            if rules.MIN_YEAR <= year <= rules.MAX_YEAR:
                found.extend(occ for occ in self.occurrences(year, region) if occ.end >= start and occ.start < stop)
        return sorted(found, key=lambda occ: (occ.start, occ.moment.id))

    def public_holidays(self, *years: int) -> set[date]:
        """Public holidays (helligdager and høytidsdager) for the given years.

        Not limited to the selectable year range, so plan-back milestones that fall in the previous year can
        still be moved off holidays.
        """
        return {
            self._resolve(moment.id, year, NATIONAL, ()).start
            for year in years
            for moment in self.moments.values()
            if moment.kind == "public_holiday"
        }


def _add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _range(entry: Mapping[str, Any], where: str) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if "date" in entry:
        if "start" in entry or "end" in entry:
            raise PlanProblem(f"{where}: give either 'date' or 'start' + 'end', not both.")
        rules.validate_rule(entry["date"])
        return entry["date"], entry["date"]
    if "start" not in entry or "end" not in entry:
        raise PlanProblem(f"{where}: needs 'date', or both 'start' and 'end'.")
    rules.validate_rule(entry["start"])
    rules.validate_rule(entry["end"])
    return entry["start"], entry["end"]


def parse_library(data: Mapping[str, Any]) -> Library:
    """Validate a parsed YAML library and build a Library. Raises PlanProblem on any contract breach."""
    regions = {str(r["id"]): str(r["name"]) for r in data.get("regions", [])}
    if NATIONAL not in regions:
        raise PlanProblem("The library must define the national region 'all'.")
    categories = dict(data.get("categories", {}))
    kinds = dict(data.get("kinds", {}))
    library = Library(str(data.get("country", "")), regions, categories, kinds)
    for raw in data.get("moments", []):
        moment_id = str(raw.get("id", ""))
        where = f"Moment {moment_id or '(no id)'}"
        if not moment_id or moment_id in library.moments:
            raise PlanProblem(f"{where}: every moment needs a unique id.")
        name = raw.get("name") or {}
        if not name.get("nb") or not name.get("en"):
            raise PlanProblem(f"{where}: needs a name in both nb and en.")
        if raw.get("kind") not in kinds:
            raise PlanProblem(f"{where}: unknown kind {raw.get('kind')!r}.")
        tags = tuple(raw.get("tags") or ())
        unknown = [tag for tag in tags if tag not in categories]
        if not tags or unknown:
            raise PlanProblem(f"{where}: needs category tags from the library ({', '.join(unknown) or 'none given'}).")
        basis = raw.get("basis")
        if basis not in BASES:
            raise PlanProblem(f"{where}: basis must be one of {', '.join(BASES)}.")
        source, notes = str(raw.get("source") or ""), " ".join(str(raw.get("notes") or "").split())
        if not source.startswith("https://") and not (basis == "convention" and notes):
            raise PlanProblem(f"{where}: needs an https source URL, or basis 'convention' with notes explaining why.")
        start, end = _range(raw, where)
        variants = []
        for item in raw.get("variants") or ():
            if item.get("region") not in regions or item.get("region") == NATIONAL:
                raise PlanProblem(f"{where}: variant region {item.get('region')!r} is not a defined sub-region.")
            if not str(item.get("source", "")).startswith("https://"):
                raise PlanProblem(f"{where}: regional variants need their own https source.")
            v_start, v_end = _range(item, f"{where} / {item['region']}")
            variants.append(Variant(item["region"], v_start, v_end, item["source"], str(item.get("verified", ""))))
        if raw.get("varies") and start == end:
            raise PlanProblem(f"{where}: a moment that varies locally must be shown as a range.")
        library.moments[moment_id] = Moment(
            id=moment_id,
            name_nb=str(name["nb"]),
            name_en=str(name["en"]),
            kind=str(raw["kind"]),
            start=start,
            end=end,
            tags=tags,
            basis=str(basis),
            source=source,
            notes=notes,
            varies=str(raw.get("varies") or ""),
            variants=tuple(variants),
        )
    # Relative rules must point at real moments.
    for moment in library.moments.values():
        for spec in (moment.start, moment.end, *(r for v in moment.variants for r in (v.start, v.end))):
            if spec["rule"] == "relative" and spec["to"] not in library.moments:
                raise PlanProblem(f"Moment {moment.id}: relative rule points at unknown moment {spec['to']!r}.")
    return library


@lru_cache(maxsize=4)
def load_library(path: str | Path = DEFAULT_LIBRARY) -> Library:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return parse_library(data)
