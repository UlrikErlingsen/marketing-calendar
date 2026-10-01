import json
import math
from datetime import date

import pytest

from seasonsignal import (
    DEFAULT_LEAD_TIMES,
    Campaign,
    PlanProblem,
    load_library,
    load_store,
    plan_back,
    plan_campaign,
    previous_working_day,
    save_store,
    validate_campaign,
    validate_lead_times,
)

LIB = load_library()


def test_plan_back_whole_weeks_from_moment_start():
    # Black Week 2026 starts Monday 23 November; food lead times are 16/10/6/1 weeks.
    milestones = plan_back(date(2026, 11, 23), DEFAULT_LEAD_TIMES["food"])
    assert [(m.key, m.due) for m in milestones] == [
        ("concept", date(2026, 8, 3)),
        ("creative", date(2026, 9, 14)),
        ("media", date(2026, 10, 12)),
        ("live", date(2026, 11, 16)),
    ]
    assert all(m.moved_from is None for m in milestones)


def test_milestones_move_off_weekends_and_public_holidays():
    holidays = LIB.public_holidays(2026, 2027)
    # 17. mai 2026 is a Sunday; one week earlier is also a Sunday → Friday 8 May.
    live = plan_back(date(2026, 5, 17), {"concept": 3, "creative": 2, "media": 1, "live": 1}, holidays)[-1]
    assert live.due == date(2026, 5, 8) and live.moved_from == date(2026, 5, 10)
    # Kristi himmelfart (Thursday 14 May 2026) → Wednesday 13 May.
    assert previous_working_day(date(2026, 5, 14), holidays) == date(2026, 5, 13)
    # Across New Year: 1 week before 1 Jan 2027 is 1. juledag (Friday) → Thursday 24 Dec.
    assert previous_working_day(date(2026, 12, 25), holidays) == date(2026, 12, 24)
    # Raw dates when working-day adjustment is off.
    raw = plan_back(date(2026, 5, 17), {"concept": 3, "creative": 2, "media": 1, "live": 1}, holidays,
                    working_days=False)
    assert raw[-1].due == date(2026, 5, 10)


def test_milestone_status():
    milestone = plan_back(date(2026, 11, 23), DEFAULT_LEAD_TIMES["food"])[2]  # media 12 Oct
    assert milestone.status(date(2026, 10, 1)) == "due soon"
    assert milestone.status(date(2026, 9, 1)) == "on track"
    assert milestone.status(date(2026, 10, 13)) == "overdue"


@pytest.mark.parametrize(
    "bad",
    [
        {"concept": 4, "creative": 6, "media": 2, "live": 1},  # out of order
        {"concept": 10, "creative": 6, "media": 4, "live": -1},
        {"concept": 10.5, "creative": 6, "media": 4, "live": 1},
        {"concept": math.nan, "creative": 6, "media": 4, "live": 1},
        {"concept": 60, "creative": 6, "media": 4, "live": 1},
        {"concept": 10, "creative": 6, "media": 4},
        {"concept": True, "creative": 0, "media": 0, "live": 0},
    ],
)
def test_lead_time_validation(bad):
    with pytest.raises(PlanProblem):
        validate_lead_times({"retail": bad})


def test_lead_times_accept_whole_floats_and_numpy_ints():
    import numpy as np

    clean = validate_lead_times({"retail": {"concept": 10.0, "creative": np.int64(6), "media": 4, "live": 0}})
    assert clean["retail"] == {"concept": 10, "creative": 6, "media": 4, "live": 0}


def test_missing_file_gives_fictional_demo(tmp_path):
    store = load_store(tmp_path / "s.json", demo_year=2026)
    assert not store.saved
    assert len(store.campaigns) == 3 and all(c.fictional and c.brand == "Fjellbrus" for c in store.campaigns)
    assert {c.moment_id for c in store.campaigns} == {"paskeferie", "syttende_mai", "black_week"}
    assert {c.category for c in store.campaigns} == {"food"}


def test_store_round_trip(tmp_path):
    path = tmp_path / "nested" / "s.json"
    store = load_store(path, demo_year=2026)
    store.campaigns.append(validate_campaign(Campaign(name="  Høst  ", moment_id="hostferie", year=2027,
                                                     category="travel", region="oslo"), LIB))
    store.lead_times["travel"]["live"] = 2
    save_store(store)
    again = load_store(path)
    assert again.saved and [c.name for c in again.campaigns][-1] == "Høst"
    assert again.lead_times["travel"]["live"] == 2
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1
    assert not path.with_suffix(".json.tmp").exists()


def test_corrupt_or_foreign_file_is_reported(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(PlanProblem):
        load_store(path)
    path.write_text('{"version": 99}', encoding="utf-8")
    with pytest.raises(PlanProblem):
        load_store(path)


def test_campaign_validation_and_plan():
    with pytest.raises(PlanProblem):
        validate_campaign(Campaign(name=" ", moment_id="syttende_mai", year=2026, category="food"), LIB)
    with pytest.raises(PlanProblem):
        validate_campaign(Campaign(name="x", moment_id="nope", year=2026, category="food"), LIB)
    with pytest.raises(PlanProblem):
        validate_campaign(Campaign(name="x", moment_id="syttende_mai", year=2040, category="food"), LIB)
    plan = plan_campaign(Campaign(name="x", moment_id="black_week", year=2026, category="food"), LIB,
                         validate_lead_times(DEFAULT_LEAD_TIMES))
    assert plan.occurrence.start == date(2026, 11, 23)
    assert plan.milestones[0].due == date(2026, 8, 3)
