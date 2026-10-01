"""My campaigns: the campaign model, the fictional demo, validation and plan-back.

Saving and loading live in ``storage.py``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .errors import PlanProblem
from .leadtimes import DEFAULT_LEAD_TIMES, Milestone, plan_back
from .moments import NATIONAL, Library, Occurrence

DEMO_BRAND = "Fjellbrus"
DEMO_NOTE = "Fictional demo brand — Fjellbrus is invented for this example and represents no real company."


@dataclass
class Campaign:
    name: str
    moment_id: str
    year: int
    category: str
    brand: str = ""
    region: str = NATIONAL
    notes: str = ""
    fictional: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Campaign":
        known = {key: raw[key] for key in cls.__dataclass_fields__ if key in raw}
        try:
            campaign = cls(**known)
            campaign.year = int(campaign.year)
        except (TypeError, ValueError) as exc:
            raise PlanProblem(f"A saved campaign is incomplete or malformed: {raw!r}") from exc
        return campaign


@dataclass(frozen=True)
class CampaignPlan:
    campaign: Campaign
    occurrence: Occurrence
    milestones: list[Milestone]


def demo_campaigns(year: int) -> list[Campaign]:
    """Three fictional Fjellbrus campaigns for the demo (Food & drink)."""
    common = {"brand": DEMO_BRAND, "year": year, "category": "food", "fictional": True}
    return [
        Campaign(
            name="Påskefjell — limited Easter flavour",
            moment_id="paskeferie",
            notes="In-store displays in mountain and cabin areas; cabin-trip social content. " + DEMO_NOTE,
            id="demo-paske",
            **common,
        ),
        Campaign(
            name="17. mai — Fjellbrus for the whole street party",
            moment_id="syttende_mai",
            notes="Family packs and russ-safe, alcohol-free positioning. " + DEMO_NOTE,
            id="demo-17mai",
            **common,
        ),
        Campaign(
            name="Black Week — multipack offer",
            moment_id="black_week",
            notes="Online grocery and chain multipack deal. " + DEMO_NOTE,
            id="demo-blackweek",
            **common,
        ),
    ]


def validate_campaign(campaign: Campaign, library: Library) -> Campaign:
    if not campaign.name.strip():
        raise PlanProblem("Give the campaign a name.")
    library.get(campaign.moment_id)
    if campaign.category not in library.categories:
        raise PlanProblem(f"Unknown category {campaign.category!r}.")
    if campaign.region not in library.regions:
        raise PlanProblem(f"Unknown region {campaign.region!r}.")
    library.resolve(campaign.moment_id, campaign.year, campaign.region)  # checks the year range too
    campaign.name = campaign.name.strip()
    return campaign


def plan_campaign(
    campaign: Campaign, library: Library, lead_times: dict[str, dict[str, int]], *, working_days: bool = True
) -> CampaignPlan:
    occurrence = library.resolve(campaign.moment_id, campaign.year, campaign.region)
    offsets = lead_times.get(campaign.category) or DEFAULT_LEAD_TIMES["retail"]
    holidays = library.public_holidays(campaign.year - 1, campaign.year)
    return CampaignPlan(campaign, occurrence, plan_back(occurrence.start, offsets, holidays, working_days=working_days))
