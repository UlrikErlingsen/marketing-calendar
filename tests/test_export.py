import io
import re
from datetime import date, datetime, timezone

import openpyxl
import pandas as pd
from icalendar import Calendar

from seasonsignal import (
    DEFAULT_LEAD_TIMES,
    build_ics,
    build_xlsx,
    campaign_items,
    demo_campaigns,
    load_library,
    moment_items,
    moments_frame,
    plan_campaign,
    plan_moments,
    safe_cell,
    select_occurrences,
    validate_lead_times,
)

LIB = load_library()
LEAD = validate_lead_times(DEFAULT_LEAD_TIMES)
STAMP = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def _planned(year=2026, region="all"):
    occurrences = select_occurrences(LIB, LIB.occurrences(year, region), "food")
    return plan_moments(LIB, occurrences, LEAD, "food")


def _ics():
    plans = [plan_campaign(c, LIB, LEAD) for c in demo_campaigns(2026)]
    return build_ics(moment_items(_planned()) + campaign_items(plans), "SeasonSignal test", stamp=STAMP)


def test_ics_is_valid_rfc5545_structure():
    raw = _ics()
    text = raw.decode("utf-8")
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.rstrip().endswith("END:VCALENDAR")
    assert "\n" not in text.replace("\r\n", "")  # CRLF line endings only
    assert all(len(line.encode("utf-8")) <= 75 for line in text.split("\r\n"))  # folded lines
    cal = Calendar.from_ical(raw)
    assert str(cal["VERSION"]) == "2.0" and "SeasonSignal" in str(cal["PRODID"])
    events = list(cal.walk("VEVENT"))
    assert events
    uids = [str(e["UID"]) for e in events]
    assert len(uids) == len(set(uids))
    for event in events:
        for prop in ("UID", "DTSTAMP", "DTSTART", "DTEND", "SUMMARY"):
            assert prop in event, prop
        start, end = event.decoded("DTSTART"), event.decoded("DTEND")
        assert type(start) is date and type(end) is date  # all-day
        assert end > start  # DTEND is exclusive
        assert str(event["TRANSP"]) == "TRANSPARENT"


def test_ics_ranges_and_milestones():
    cal = Calendar.from_ical(_ics())
    by_uid = {str(e["UID"]): e for e in cal.walk("VEVENT")}
    week = by_uid["moment-black-week-2026-all@seasonsignal.local"]
    assert week.decoded("DTSTART") == date(2026, 11, 23) and week.decoded("DTEND") == date(2026, 12, 1)
    concept = by_uid["milestone-black-week-2026-all-concept@seasonsignal.local"]
    assert concept.decoded("DTSTART") == date(2026, 8, 3)
    vinter = by_uid["moment-vinterferie-2026-all@seasonsignal.local"]
    assert "varierer lokalt" in str(vinter["SUMMARY"])
    assert any(str(uid).startswith("campaign-demo-blackweek") for uid in by_uid)


def test_ics_uids_are_stable_between_exports():
    first = re.findall(r"UID:(.*)", _ics().decode())
    second = re.findall(r"UID:(.*)", _ics().decode())
    assert first == second


def test_formula_injection_is_neutralised():
    assert safe_cell("=HYPERLINK(\"x\")") == "'=HYPERLINK(\"x\")"
    assert safe_cell("+47 22") == "'+47 22"
    assert safe_cell("normal\x07") == "normal"
    assert safe_cell(5) == 5


def test_xlsx_plan_has_sheets_and_dates():
    frame = moments_frame(LIB, _planned(), date(2026, 10, 1))
    evil = pd.DataFrame([{"Campaign": "=1+1", "id": "x"}])
    data = build_xlsx({"Moments": frame, "Campaigns": evil})
    book = openpyxl.load_workbook(io.BytesIO(data))
    assert book.sheetnames == ["Moments", "Campaigns"]
    sheet = book["Moments"]
    headers = [c.value for c in sheet[1]]
    assert "Concept & brief" in headers and "id" not in headers
    assert book["Campaigns"]["A2"].value == "'=1+1"
