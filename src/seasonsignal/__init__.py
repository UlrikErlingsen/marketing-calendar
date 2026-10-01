"""SeasonSignal: the Norwegian marketing year, computed.

Public API — import from here, not from submodules, so a future Signal Hub can depend on a stable surface.
This package never imports streamlit; the UI lives in ``app.py``.
"""

__version__ = "1.0.0"

MIN_YEAR = 2025
MAX_YEAR = 2035

# Constants above are imported by submodules, so they must be defined before these imports.
from .campaigns import Campaign, CampaignPlan, demo_campaigns, plan_campaign, validate_campaign  # noqa: E402
from .errors import PlanProblem, friendly_message  # noqa: E402
from .export import (  # noqa: E402
    CalendarItem,
    about_frame,
    build_ics,
    build_xlsx,
    campaign_items,
    moment_items,
    safe_cell,
)
from .leadtimes import (  # noqa: E402
    DEFAULT_LEAD_TIMES,
    MILESTONES,
    Milestone,
    plan_back,
    previous_working_day,
    validate_lead_times,
)
from .moments import NATIONAL, Library, Moment, Occurrence, load_library, parse_library  # noqa: E402
from .planner import (  # noqa: E402
    PlannedMoment,
    campaigns_frame,
    lead_times_frame,
    milestones_frame,
    moments_frame,
    plan_moments,
    planning_status,
    select_occurrences,
)
from .rules import easter_sunday, evaluate, iso_week_day, nth_weekday  # noqa: E402
from .storage import Store, default_store_path, load_store, save_store, update_store  # noqa: E402

__all__ = [
    "__version__",
    "MIN_YEAR",
    "MAX_YEAR",
    "NATIONAL",
    "DEFAULT_LEAD_TIMES",
    "MILESTONES",
    "CalendarItem",
    "Campaign",
    "CampaignPlan",
    "Library",
    "Milestone",
    "Moment",
    "Occurrence",
    "PlanProblem",
    "PlannedMoment",
    "Store",
    "about_frame",
    "build_ics",
    "build_xlsx",
    "campaign_items",
    "campaigns_frame",
    "default_store_path",
    "demo_campaigns",
    "easter_sunday",
    "evaluate",
    "friendly_message",
    "iso_week_day",
    "lead_times_frame",
    "load_library",
    "load_store",
    "milestones_frame",
    "moment_items",
    "moments_frame",
    "nth_weekday",
    "parse_library",
    "plan_back",
    "plan_campaign",
    "plan_moments",
    "planning_status",
    "previous_working_day",
    "safe_cell",
    "save_store",
    "select_occurrences",
    "update_store",
    "validate_campaign",
    "validate_lead_times",
]
