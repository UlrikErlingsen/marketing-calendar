"""Exports: an RFC 5545 .ics calendar (moments, milestones, campaigns) and an XLSX plan."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from icalendar import Calendar, Event

from . import __version__
from .campaigns import CampaignPlan
from .planner import PlannedMoment

PRODID = f"-//Signal suite//SeasonSignal {__version__}//EN"
UID_DOMAIN = "seasonsignal.local"
SEQUENCE_EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class CalendarItem:
    uid: str
    summary: str
    start: date
    end: date  # inclusive
    description: str = ""
    url: str = ""
    category: str = ""


def _uid(*parts: object) -> str:
    slug = "-".join(re.sub(r"[^A-Za-z0-9]+", "-", str(part)).strip("-").lower() for part in parts)
    return f"{slug}@{UID_DOMAIN}"


def moment_items(planned: list[PlannedMoment], *, milestones: bool = True, category: str = "") -> list[CalendarItem]:
    """Calendar items for moments and (optionally) their milestones.

    Milestone dates depend on the planning category's lead times, so ``category`` is part of their UID: a Food
    plan and a Retail plan are different events, not two versions of one.
    """
    items = []
    for item in planned:
        occ, moment = item.occurrence, item.occurrence.moment
        detail = [moment.display_name, moment.notes]
        if occ.varies_here:
            detail.insert(0, "Dates vary by municipality (kommune) — this is the national range. Check the local school calendar (skolerute).")
        detail.append(f"Source: {occ.source}")
        items.append(
            CalendarItem(
                uid=_uid("moment", moment.id, occ.year, occ.region),
                summary=moment.display_name + (" (varies locally)" if occ.varies_here else ""),
                start=occ.start,
                end=occ.end,
                description="\n\n".join(part for part in detail if part),
                url=occ.source,
                category="Moment",
            )
        )
        if milestones:
            for milestone in item.milestones:
                items.append(
                    CalendarItem(
                        uid=_uid("milestone", moment.id, occ.year, occ.region, category or "plan", milestone.key),
                        summary=f"{milestone.label}: {moment.display_name}",
                        start=milestone.due,
                        end=milestone.due,
                        description=(
                            f"{milestone.weeks_before} weeks before {moment.display_name} ({occ.start:%d.%m.%Y}). "
                            "Planned with Season Signal lead times."
                        ),
                        category="Milestone",
                    )
                )
    return items


def campaign_items(plans: list[CampaignPlan]) -> list[CalendarItem]:
    items = []
    for plan in plans:
        campaign, occ = plan.campaign, plan.occurrence
        prefix = f"{campaign.brand}: " if campaign.brand else ""
        for milestone in plan.milestones:
            items.append(
                CalendarItem(
                    uid=_uid("campaign", campaign.id, milestone.key),
                    summary=f"{prefix}{milestone.label} — {campaign.name}",
                    start=milestone.due,
                    end=milestone.due,
                    description=(
                        f"Campaign for {occ.moment.display_name} ({occ.start:%d.%m.%Y}), {milestone.weeks_before} weeks "
                        f"before.\n\n{campaign.notes}"
                    ).strip(),
                    category="Campaign",
                )
            )
    return items


def build_ics(items: list[CalendarItem], name: str = "Season Signal", *, stamp: datetime | None = None) -> bytes:
    """All-day events (DTEND exclusive, per RFC 5545), transparent so they never block busy time.

    Every event carries LAST-MODIFIED and a SEQUENCE that grows with the export time (minutes since 2025), so a
    calendar that honours them treats a newer export as an update of the same UID.
    """
    stamp = stamp or datetime.now(timezone.utc).replace(microsecond=0)
    sequence = max(0, int((stamp - SEQUENCE_EPOCH).total_seconds() // 60))
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", name)
    cal.add("x-wr-timezone", "Europe/Oslo")
    seen: set[str] = set()
    for item in items:
        if item.uid in seen:
            continue
        seen.add(item.uid)
        event = Event()
        event.add("uid", item.uid)
        event.add("dtstamp", stamp)
        event.add("last-modified", stamp)
        event.add("sequence", sequence)
        event.add("summary", item.summary)
        event.add("dtstart", item.start)
        event.add("dtend", item.end + timedelta(days=1))
        event.add("transp", "TRANSPARENT")
        if item.description:
            event.add("description", item.description)
        if item.url:
            event.add("url", item.url)
        if item.category:
            event.add("categories", [item.category])
        cal.add_component(event)
    return cal.to_ical()


def safe_cell(value: object) -> object:
    """Neutralise spreadsheet formula injection and strip control characters in text cells."""
    if not isinstance(value, str):
        return value
    text = _CONTROL.sub("", value)
    return "'" + text if text.startswith(_FORMULA_START) else text


def build_xlsx(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for title, frame in sheets.items():
            clean = frame.drop(columns=[c for c in ("id", "key") if c in frame.columns])
            clean = clean.rename(columns=lambda c: safe_cell(str(c))).map(safe_cell)
            clean.to_excel(writer, sheet_name=title[:31], index=False)
            sheet = writer.sheets[title[:31]]
            sheet.freeze_panes = "A2"
            for column_cells in sheet.columns:
                longest = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(10, longest + 2), 60)
                for cell in column_cells[1:]:
                    if isinstance(cell.value, (date, datetime)):
                        cell.number_format = "DD.MM.YYYY"
    return buffer.getvalue()


def about_frame(year: int, region: str, category: str, generated: date | None = None) -> pd.DataFrame:
    generated = generated or date.today()
    rows = [
        ("Tool", f"Season Signal {__version__} — part of the Signal suite"),
        ("Generated", generated.isoformat()),
        ("Year", year),
        ("Region", region),
        ("Planning category", category),
        (
            "Read this",
            "Dates are computed from rules in the moments library. Moments marked 'varies locally' show a national "
            "range — check the municipality's school calendar (skolerute). Lead times are editable planning conventions, not research.",
        ),
        ("Demo data", "Fjellbrus and its campaigns are fictional; the demo is Norwegian because the tool is built for the Norwegian market."),
    ]
    return pd.DataFrame(rows, columns=["Field", "Value"])
