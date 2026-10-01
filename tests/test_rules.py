from datetime import date

import pytest

from seasonsignal import PlanProblem, easter_sunday, evaluate, iso_week_day, load_library, nth_weekday

LIB = load_library()

# Easter Sunday for known years (Western computus).
EASTER = {
    2025: date(2025, 4, 20),
    2026: date(2026, 4, 5),
    2027: date(2027, 3, 28),
    2028: date(2028, 4, 16),
    2029: date(2029, 4, 1),
    2030: date(2030, 4, 21),
    2035: date(2035, 3, 25),
}

# Easter-dependent helligdager, checked against the Norwegian holiday calendar for each year.
EASTER_HOLIDAYS = {
    2025: {
        "skjaertorsdag": date(2025, 4, 17),
        "langfredag": date(2025, 4, 18),
        "andre_paskedag": date(2025, 4, 21),
        "kristi_himmelfart": date(2025, 5, 29),
        "pinsedag": date(2025, 6, 8),
        "andre_pinsedag": date(2025, 6, 9),
    },
    2026: {
        "skjaertorsdag": date(2026, 4, 2),
        "langfredag": date(2026, 4, 3),
        "andre_paskedag": date(2026, 4, 6),
        "kristi_himmelfart": date(2026, 5, 14),
        "pinsedag": date(2026, 5, 24),
        "andre_pinsedag": date(2026, 5, 25),
    },
    2027: {
        "skjaertorsdag": date(2027, 3, 25),
        "langfredag": date(2027, 3, 26),
        "andre_paskedag": date(2027, 3, 29),
        "kristi_himmelfart": date(2027, 5, 6),
        "pinsedag": date(2027, 5, 16),
        "andre_pinsedag": date(2027, 5, 17),  # coincides with 17. mai
    },
    2028: {
        "skjaertorsdag": date(2028, 4, 13),
        "langfredag": date(2028, 4, 14),
        "andre_paskedag": date(2028, 4, 17),
        "kristi_himmelfart": date(2028, 5, 25),
        "pinsedag": date(2028, 6, 4),
        "andre_pinsedag": date(2028, 6, 5),
    },
}


@pytest.mark.parametrize("year,expected", EASTER.items())
def test_easter_sunday_known_years(year, expected):
    assert easter_sunday(year) == expected
    assert LIB.resolve("paskedag", year).start == expected


@pytest.mark.parametrize("year", EASTER_HOLIDAYS)
def test_easter_based_holidays(year):
    for moment_id, expected in EASTER_HOLIDAYS[year].items():
        assert LIB.resolve(moment_id, year).start == expected, moment_id


def test_kristi_himmelfart_is_always_thursday_and_pinse_sunday():
    for year in range(2025, 2036):
        assert LIB.resolve("kristi_himmelfart", year).start.weekday() == 3
        assert LIB.resolve("pinsedag", year).start.weekday() == 6
        assert LIB.resolve("skjaertorsdag", year).start.weekday() == 3


def test_public_holidays_set_for_2026():
    holidays = LIB.public_holidays(2026)
    assert len(holidays) == 12  # 10 helligdager on weekdays/Sundays + 1. mai + 17. mai (Sundays not listed)
    assert {date(2026, 1, 1), date(2026, 5, 1), date(2026, 5, 17), date(2026, 12, 25), date(2026, 12, 26)} <= holidays


@pytest.mark.parametrize(
    "year,morsdag,farsdag",
    [
        (2025, date(2025, 2, 9), date(2025, 11, 9)),
        (2026, date(2026, 2, 8), date(2026, 11, 8)),
        (2027, date(2027, 2, 14), date(2027, 11, 14)),
        (2028, date(2028, 2, 13), date(2028, 11, 12)),
    ],
)
def test_morsdag_and_farsdag_second_sundays(year, morsdag, farsdag):
    assert LIB.resolve("morsdag", year).start == morsdag
    assert LIB.resolve("farsdag", year).start == farsdag


def test_morsdag_is_february_not_may_in_every_year():
    for year in range(2025, 2036):
        day = LIB.resolve("morsdag", year).start
        assert day.month == 2 and day.weekday() == 6 and 8 <= day.day <= 14


@pytest.mark.parametrize(
    "year,black_friday",
    [(2025, date(2025, 11, 28)), (2026, date(2026, 11, 27)), (2027, date(2027, 11, 26)), (2028, date(2028, 11, 24))],
)
def test_black_friday_week_and_cyber_monday(year, black_friday):
    assert LIB.resolve("black_friday", year).start == black_friday
    week = LIB.resolve("black_week", year)
    assert week.start.weekday() == 0 and week.start == black_friday.replace(day=black_friday.day - 4)
    assert LIB.resolve("cyber_monday", year).start == week.end
    assert week.end.weekday() == 0


def test_first_advent_range_and_known_dates():
    assert LIB.resolve("forste_advent", 2025).start == date(2025, 11, 30)
    assert LIB.resolve("forste_advent", 2026).start == date(2026, 11, 29)
    for year in range(2025, 2036):
        day = LIB.resolve("forste_advent", year).start
        assert day.weekday() == 6 and date(year, 11, 27) <= day <= date(year, 12, 3)
        assert (date(year, 12, 25) - day).days // 7 in (3, 4)


def test_iso_week_ranges():
    assert iso_week_day(2026, 8, 0) == date(2026, 2, 16)
    assert iso_week_day(2027, 1, 0) == date(2027, 1, 4)
    assert iso_week_day(2026, 53, 6) == date(2027, 1, 3)  # 2026 has 53 ISO weeks
    with pytest.raises(PlanProblem):
        iso_week_day(2027, 53, 0)
    vinter = LIB.resolve("vinterferie", 2026)
    assert (vinter.start, vinter.end) == (date(2026, 2, 16), date(2026, 2, 27))
    assert vinter.varies_here
    fellesferie = LIB.resolve("fellesferie", 2026)
    assert (fellesferie.start, fellesferie.end) == (date(2026, 7, 6), date(2026, 7, 24))  # NHO/Fellesforbundet 2026


@pytest.mark.parametrize(
    "moment_id,year,start,end",
    [
        ("vinterferie", 2027, date(2027, 2, 22), date(2027, 2, 26)),
        ("vinterferie", 2028, date(2028, 2, 21), date(2028, 2, 25)),
        ("hostferie", 2026, date(2026, 9, 28), date(2026, 10, 2)),
        ("hostferie", 2027, date(2027, 10, 4), date(2027, 10, 8)),
        ("paskeferie", 2027, date(2027, 3, 22), date(2027, 3, 30)),
        ("paskeferie", 2028, date(2028, 4, 10), date(2028, 4, 18)),
        ("skolestart", 2026, date(2026, 8, 17), date(2026, 8, 17)),
        ("skolestart", 2027, date(2027, 8, 16), date(2027, 8, 16)),
        ("skolestart", 2028, date(2028, 8, 21), date(2028, 8, 21)),
    ],
)
def test_oslo_rules_reproduce_published_skolerute(moment_id, year, start, end):
    occ = LIB.resolve(moment_id, year, "oslo")
    assert (occ.start, occ.end) == (start, end)
    assert occ.regional and not occ.varies_here


def test_school_christmas_break_crosses_new_year():
    occ = LIB.resolve("juleferie", 2028)  # 2028 is a leap year: year_offset, not +365 days
    assert occ.start == date(2028, 12, 19) and occ.end == date(2029, 1, 3)


def test_nth_weekday_last_and_invalid():
    assert nth_weekday(2026, 5, 0, -1) == date(2026, 5, 25)
    with pytest.raises(PlanProblem):
        nth_weekday(2026, 2, 6, 5)


def test_rule_validation_errors():
    with pytest.raises(PlanProblem):
        evaluate({"rule": "lunar"}, 2026)
    with pytest.raises(PlanProblem):
        evaluate({"rule": "nth_weekday", "month": 2, "weekday": "sunday-ish", "n": 2}, 2026)
    with pytest.raises(PlanProblem):
        evaluate({"rule": "relative", "to": "black_friday"}, 2026)  # no library to resolve against


def test_year_range_is_enforced():
    with pytest.raises(PlanProblem):
        LIB.resolve("syttende_mai", 2024)
    with pytest.raises(PlanProblem):
        LIB.resolve("syttende_mai", 2036)


@pytest.mark.parametrize(
    "region,moment_id,year,start,end",
    [
        # Bergen kommune, veiledende skolerute 2026/27 and 2027/28
        ("bergen", "hostferie", 2026, date(2026, 10, 5), date(2026, 10, 9)),
        ("bergen", "hostferie", 2027, date(2027, 10, 11), date(2027, 10, 15)),
        ("bergen", "vinterferie", 2027, date(2027, 3, 1), date(2027, 3, 5)),
        ("bergen", "vinterferie", 2028, date(2028, 2, 28), date(2028, 3, 3)),
        ("bergen", "paskeferie", 2027, date(2027, 3, 22), date(2027, 3, 29)),
        ("bergen", "paskeferie", 2028, date(2028, 4, 10), date(2028, 4, 17)),
        # Trondheim kommune skoleruta 2026/27 and 2027/28
        ("trondheim", "skolestart", 2026, date(2026, 8, 17), date(2026, 8, 17)),
        ("trondheim", "skolestart", 2027, date(2027, 8, 23), date(2027, 8, 23)),
        ("trondheim", "hostferie", 2026, date(2026, 10, 5), date(2026, 10, 9)),
        ("trondheim", "hostferie", 2027, date(2027, 10, 11), date(2027, 10, 15)),
        ("trondheim", "vinterferie", 2027, date(2027, 2, 22), date(2027, 2, 26)),
        ("trondheim", "vinterferie", 2028, date(2028, 2, 21), date(2028, 2, 25)),
        ("trondheim", "paskeferie", 2027, date(2027, 3, 22), date(2027, 3, 29)),
        ("trondheim", "paskeferie", 2028, date(2028, 4, 10), date(2028, 4, 17)),
    ],
)
def test_bergen_and_trondheim_rules_reproduce_published_skolerute(region, moment_id, year, start, end):
    occ = LIB.resolve(moment_id, year, region)
    assert (occ.start, occ.end) == (start, end)
    assert occ.regional


def test_bergen_skolestart_falls_back_to_the_national_range():
    occ = LIB.resolve("skolestart", 2026, "bergen")
    assert not occ.regional and occ.varies_here
    assert occ.start <= date(2026, 8, 14) <= occ.end  # Bergen's Friday 14 Aug 2026 lies inside the range
