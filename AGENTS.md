# AGENTS.md — SeasonSignal (repo: marketing-calendar)

You are building **SeasonSignal**, a small new product in Ulrik Erlingsen's **Signal** suite
(open-source, local-first marketing tools; see sibling repos such as `brand-tracking`
= TrackSignal for house style). This repo starts empty except for this file, a README stub,
LICENSE and .gitignore. This is the quick win of the set: keep it small and polished.

## What it is

An open **Norwegian marketing calendar and campaign planner**. It lists the commercial
moments of the Norwegian year, works backwards to planning deadlines, and exports to any
calendar app. Replaces the spreadsheets and paid planning add-ons (e.g. CoSchedule-style
calendars) that small Norwegian marketing teams use.

## The question it answers

> What are the Norwegian moments that matter for my category in the next 6–12 months,
> and when do I have to start each campaign to hit them?

## v1 scope

1. **Moments library** in `src/seasonsignal/moments/no.yaml` — each moment: id, name (nb + en),
   date rule, category tags (retail, food, fashion, travel, B2B, alcohol-free, kids…), notes,
   source URL where a date is official. Seed with, at minimum:
   - Official public holidays (computed, incl. Easter-dependent ones: skjærtorsdag, langfredag,
     påske, Kristi himmelfart, pinse) and 17. mai.
   - Retail moments: Black Week / Black Friday, Cyber Monday, Singles' Day (11.11), Valentines,
     Morsdag (2nd Sunday in February in Norway), Farsdag (2nd Sunday in November), Halloween,
     advent/julehandel, romjul/mellomjul sales.
   - Seasonal life moments: vinterferie (week 8 or 9, varies by region), påskeferie,
     russetid (late April → 17. mai), skoleslutt, fellesferie (traditionally July),
     skolestart (mid-August), høstferie (around week 40, varies by kommune), julebord season.
   - **Verify every date rule** against an official or authoritative source and put the URL in
     the YAML; where dates vary by kommune/fylke, say so and show a range instead of a date.
2. **Lead times** — per category, default planning offsets (e.g. concept −10 weeks, creative
   −6, media booking −4, live −1). User-editable.
3. **Planner view** (Streamlit) — 12-month timeline (plotly), filter by category and region,
   click a moment to see its plan-back milestones.
4. **My campaigns** — add own campaigns linked to a moment; saved to a local JSON/SQLite file.
5. **Export** — `.ics` file (moments + milestones) importable into Google/Outlook/Apple calendar;
   XLSX plan export.
6. **Year selector** — any year 2025–2035; all dates computed, nothing hard-coded per year.

Out of scope: accounts, sync, sending reminders, scraping.

## Demo

Preloaded: year = current year, category "Food & drink", one fictional brand "Fjellbrus"
with three example campaigns (påske, 17. mai, Black Week). Mark as fictional.

## Stack and house style

- Python 3.10+, Streamlit `app.py`, package `src/seasonsignal/`, tests in `tests/`.
- pandas, plotly, openpyxl, pyyaml, `icalendar`, `python-dateutil` (Easter computation).
- `pyproject.toml` (setuptools, AGPL-3.0-or-later, author "Ulrik Erlingsen"), `requirements.txt`,
  `Dockerfile`, `run_app.bat` — mirror `brand-tracking`.
- ruff (line length 120) + pytest. Tests: Easter-based holidays for several known years,
  Morsdag/Farsdag rules, ISO-week ranges, ICS validity, lead-time maths.
- README in TrackSignal's structure; CHANGELOG, SECURITY, PRIVACY, CONTRIBUTING.

## Definition of done for v1

- `run_app.bat` opens the planner; `.ics` export imports cleanly into Google Calendar.
- Every seeded moment has a source URL or a note explaining why it's a convention.
- `pytest` and `ruff check` pass; screenshots in `assets/`.

## Working rules

- Ulrik commits and pushes from **GitHub Desktop** himself; you do not push.
- Small logical commits; short summary at the end of each session.
