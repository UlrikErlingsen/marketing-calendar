import copy
from datetime import date

import pytest
import yaml

from seasonsignal import MAX_YEAR, MIN_YEAR, PlanProblem, load_library, parse_library
from seasonsignal.moments import DEFAULT_LIBRARY

LIB = load_library()
RAW = yaml.safe_load(DEFAULT_LIBRARY.read_text(encoding="utf-8"))

REQUIRED_MOMENTS = {
    # official holidays
    "nyttarsdag", "skjaertorsdag", "langfredag", "paskedag", "andre_paskedag", "forste_mai", "syttende_mai",
    "kristi_himmelfart", "pinsedag", "andre_pinsedag", "forste_juledag", "andre_juledag",
    # retail
    "black_week", "black_friday", "cyber_monday", "singles_day", "valentinsdag", "morsdag", "farsdag",
    "halloween", "julehandel", "romjul",
    # seasons
    "vinterferie", "paskeferie", "russetid", "skoleslutt", "fellesferie", "skolestart", "hostferie", "julebord",
}  # fmt: skip


def test_brief_minimum_moments_are_seeded():
    assert REQUIRED_MOMENTS <= set(LIB.moments)


def test_every_moment_has_source_or_convention_note():
    for moment in LIB.moments.values():
        has_source = moment.source.startswith("https://")
        assert has_source or (moment.basis == "convention" and moment.notes), moment.id
        assert moment.notes, f"{moment.id} needs notes"


def test_locally_set_moments_are_ranges_with_notes():
    for moment in LIB.moments.values():
        if moment.varies:
            assert moment.is_range, moment.id
            assert "kommune" in moment.notes or "locally" in moment.notes, moment.id


def test_every_moment_resolves_for_every_year_and_region():
    for year in range(MIN_YEAR, MAX_YEAR + 1):
        for region in LIB.regions:
            for occ in LIB.occurrences(year, region):
                assert occ.start <= occ.end
                assert occ.days <= 45, occ.moment.id


def test_window_crosses_year_boundary():
    found = LIB.window(date(2026, 10, 1), 6)
    ids = {occ.moment.id for occ in found}
    assert {"black_week", "syttende_mai"} - ids == {"syttende_mai"}  # 17. mai is outside a 6-month window
    assert any(occ.start.year == 2027 for occ in found)
    assert "syttende_mai" in {occ.moment.id for occ in LIB.window(date(2026, 10, 1), 12)}


def _with(change):
    data = copy.deepcopy(RAW)
    change(data)
    return data


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["moments"][0].update(source="", basis="official"),  # official without source
        lambda d: d["moments"][0].update(tags=["not-a-category"]),
        lambda d: d["moments"][0].update(basis="vibes"),
        lambda d: d["moments"][1].update(id=d["moments"][0]["id"]),  # duplicate id
        lambda d: d["moments"].append({**d["moments"][0], "id": "x", "start": d["moments"][0]["date"]}),
        lambda d: next(m for m in d["moments"] if m["id"] == "vinterferie")["variants"][0].update(region="bergen"),
        lambda d: next(m for m in d["moments"] if m["id"] == "cyber_monday")["date"].update(to="nope"),
    ],
)
def test_library_contract_rejects_bad_entries(change):
    with pytest.raises(PlanProblem):
        parse_library(_with(change))


def test_convention_without_source_is_allowed_with_notes():
    data = _with(lambda d: d["moments"].append(
        {"id": "x", "name": {"nb": "X", "en": "X"}, "kind": "retail", "date": {"rule": "fixed", "month": 3, "day": 3},
         "tags": ["retail"], "basis": "convention", "notes": "No owner; a trade habit."}
    ))
    assert "x" in parse_library(data).moments


def test_circular_relative_rules_are_caught():
    def loop(d):
        d["moments"].append({"id": "a", "name": {"nb": "A", "en": "A"}, "kind": "retail", "tags": ["retail"],
                             "basis": "convention", "notes": "n", "date": {"rule": "relative", "to": "b"}})
        d["moments"].append({"id": "b", "name": {"nb": "B", "en": "B"}, "kind": "retail", "tags": ["retail"],
                             "basis": "convention", "notes": "n", "date": {"rule": "relative", "to": "a"}})

    library = parse_library(_with(loop))
    with pytest.raises(PlanProblem, match="Circular"):
        library.resolve("a", 2026)


def test_window_includes_ranges_that_started_last_year():
    found = {occ.moment.id for occ in LIB.window(date(2027, 1, 1), 6)}
    assert "juleferie" in found  # 19.12.2026 – 03.01.2027
