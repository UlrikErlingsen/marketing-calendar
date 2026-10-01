"""Planner tables: the selected moments with their plan-back milestones, shared by the app and the exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import rules
from .campaigns import CampaignPlan
from .leadtimes import DEFAULT_LEAD_TIMES, MILESTONES, Milestone, plan_back
from .moments import NATIONAL, Library, Occurrence


@dataclass(frozen=True)
class PlannedMoment:
    occurrence: Occurrence
    milestones: list[Milestone]


def select_occurrences(
    library: Library,
    occurrences: list[Occurrence],
    category: str | None,
    *,
    include_all: bool = False,
    include_public_holidays: bool = True,
) -> list[Occurrence]:
    """Keep moments tagged with ``category``; optionally everything, and public holidays as context."""
    if include_all or not category:
        return list(occurrences)
    return [
        occ
        for occ in occurrences
        if category in occ.moment.tags or (include_public_holidays and occ.moment.kind == "public_holiday")
    ]


def plan_moments(
    library: Library,
    occurrences: list[Occurrence],
    lead_times: dict[str, dict[str, int]],
    category: str | None,
    *,
    working_days: bool = True,
) -> list[PlannedMoment]:
    offsets = lead_times.get(category or "", DEFAULT_LEAD_TIMES["retail"])
    years = sorted({occ.start.year for occ in occurrences})
    holidays = library.public_holidays(*{y for year in years for y in (year - 1, year)})
    return [PlannedMoment(occ, plan_back(occ.start, offsets, holidays, working_days=working_days)) for occ in occurrences]


def planning_status(item: PlannedMoment, today: date) -> str:
    """Where a moment stands for a team starting today."""
    occ = item.occurrence
    concept = next(m for m in item.milestones if m.key == "concept")
    if occ.end < today:
        return "passed"
    if occ.start <= today:
        return "happening now"
    if concept.due >= today:
        return "start soon" if (concept.due - today).days <= 14 else "on track"
    return "behind plan"


def moments_frame(library: Library, planned: list[PlannedMoment], today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    rows = []
    for item in planned:
        occ, moment = item.occurrence, item.occurrence.moment
        rows.append(
            {
                "Moment": moment.name_nb,
                "Moment (en)": moment.name_en,
                "Kind": library.kinds.get(moment.kind, {}).get("en", moment.kind),
                "Start": occ.start,
                "End": occ.end,
                "Varies locally": "Yes — range" if occ.varies_here else ("Regional rule" if occ.regional else ""),
                "Region": library.regions.get(occ.region, occ.region),
                "Categories": ", ".join(library.category_label(tag) for tag in moment.tags),
                **{label: next(m.due for m in item.milestones if m.key == key) for key, label in MILESTONES},
                "Status": planning_status(item, today),
                "Basis": moment.basis,
                "Rule": rules.describe(moment.start)
                + ("" if moment.start == moment.end else f" → {rules.describe(moment.end)}"),
                "Source": occ.source,
                "Notes": moment.notes,
                "id": moment.id,
            }
        )
    return pd.DataFrame(rows)


def milestones_frame(planned: list[PlannedMoment], today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    rows = [
        {
            "Moment": item.occurrence.moment.name_nb,
            "Moment start": item.occurrence.start,
            "Milestone": milestone.label,
            "Weeks before": milestone.weeks_before,
            "Due": milestone.due,
            "Moved off weekend/holiday": milestone.moved_from or "",
            "Status": milestone.status(today),
        }
        for item in planned
        for milestone in item.milestones
    ]
    return pd.DataFrame(rows)


def campaigns_frame(library: Library, plans: list[CampaignPlan], today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    rows = []
    for plan in plans:
        campaign, occ = plan.campaign, plan.occurrence
        next_due = next((m for m in plan.milestones if m.due >= today), None)
        rows.append(
            {
                "Campaign": campaign.name,
                "Brand": campaign.brand,
                "Moment": occ.moment.name_nb,
                "Year": campaign.year,
                "Region": library.regions.get(campaign.region, campaign.region),
                "Category": library.category_label(campaign.category),
                "Moment start": occ.start,
                **{label: next(m.due for m in plan.milestones if m.key == key) for key, label in MILESTONES},
                "Next milestone": f"{next_due.label} — {next_due.due:%d.%m.%Y}" if next_due else "All milestones passed",
                "Fictional": "Yes" if campaign.fictional else "",
                "Notes": campaign.notes,
                "id": campaign.id,
            }
        )
    return pd.DataFrame(rows)


def lead_times_frame(library: Library, lead_times: dict[str, dict[str, int]]) -> pd.DataFrame:
    rows = [
        {"Category": library.category_label(key), "key": key, **{label: offsets[k] for k, label in MILESTONES}}
        for key, offsets in lead_times.items()
        if key in library.categories
    ]
    return pd.DataFrame(rows)


def region_label(library: Library, region: str) -> str:
    return library.regions.get(region, library.regions[NATIONAL])
