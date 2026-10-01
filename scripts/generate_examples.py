"""Regenerate the committed example exports in examples/ (deterministic: fixed 'today' and DTSTAMP).

    python scripts/generate_examples.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seasonsignal import (  # noqa: E402
    DEFAULT_LEAD_TIMES,
    about_frame,
    build_ics,
    build_xlsx,
    campaign_items,
    campaigns_frame,
    demo_campaigns,
    lead_times_frame,
    load_library,
    milestones_frame,
    moment_items,
    moments_frame,
    plan_campaign,
    plan_moments,
    select_occurrences,
    validate_lead_times,
)

EXAMPLES = ROOT / "examples"
YEAR = 2026
TODAY = date(2026, 10, 1)
STAMP = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def build() -> dict[str, bytes]:
    library = load_library()
    lead_times = validate_lead_times(DEFAULT_LEAD_TIMES)
    food = plan_moments(library, select_occurrences(library, library.occurrences(YEAR), "food"), lead_times, "food")
    everything = plan_moments(library, library.occurrences(YEAR), lead_times, "retail")
    plans = [plan_campaign(c, library, lead_times) for c in demo_campaigns(YEAR)]
    return {
        # Moments only, every category — a plain "Norwegian marketing year" calendar.
        f"seasonsignal-{YEAR}-moments.ics": build_ics(
            moment_items(everything, milestones=False), f"Norwegian marketing year {YEAR}", stamp=STAMP
        ),
        # The demo: Food & drink moments, plan-back milestones and the fictional Fjellbrus campaigns.
        f"seasonsignal-{YEAR}-food-fjellbrus-demo.ics": build_ics(
            moment_items(food, category="food") + campaign_items(plans), f"Season Signal {YEAR} — Food & drink (demo)",
            stamp=STAMP,
        ),
        f"seasonsignal-{YEAR}-food-fjellbrus-demo.xlsx": build_xlsx(
            {
                "Moments": moments_frame(library, food, TODAY),
                "Milestones": milestones_frame(food, TODAY),
                "Campaigns": campaigns_frame(library, plans, TODAY),
                "Lead times": lead_times_frame(library, lead_times),
                "About": about_frame(YEAR, "Hele landet", "Food & drink", TODAY),
            }
        ),
    }


def main() -> None:
    EXAMPLES.mkdir(exist_ok=True)
    for name, payload in build().items():
        (EXAMPLES / name).write_bytes(payload)
        print(f"wrote examples/{name}")


if __name__ == "__main__":
    main()
