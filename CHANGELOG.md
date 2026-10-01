# Changelog

## 1.0.0 — unreleased

First version of **SeasonSignal**, the Norwegian marketing calendar in the Signal suite.

### Moments library

- 39 Norwegian moments in `src/seasonsignal/moments/no.yaml`, each with nb + en names, a date rule, category tags, notes, a basis (official / tradition / observed / convention) and a source URL. Rules and links reviewed on 1 October 2026.
- Computed public holidays, including Easter-based skjærtorsdag, langfredag, påske, Kristi himmelfart and pinse (Lovdata), plus 1. and 17. mai.
- Retail moments: Black Friday, Black Week (Monday → Cyber Monday), Cyber Monday, Singles' Day, Valentine's, morsdag (2nd Sunday of February), farsdag (2nd Sunday of November), Halloween, first Sunday of Advent, julehandel, romjul/mellomjulssalg, feriepenger.
- Seasons: vinterferie, påskeferie, russetid, skoleslutt, fellesferie, skolestart, høstferie, juleferie and julebord. School breaks that vary by kommune are shown as national ranges; Oslo, Bergen and Trondheim have verified regional rules (two school years each).

### Planning

- Default lead times per category (concept, creative, media booking, live), editable and saved locally.
- Plan-back milestones move off weekends and public holidays to the previous working day.
- Streamlit planner: 12-month timeline (click a moment for its milestones), "coming up" view across the year boundary, my campaigns, lead-time editor, sources page. Any year 2025–2035.
- Exports: RFC 5545 `.ics` (all-day, transparent events with stable UIDs) and an XLSX plan with formula-injection-safe cells.
- Fictional demo brand Fjellbrus (Food & drink) with påske, 17. mai and Black Week campaigns.

### Planning status

- Moments are graded on track / start soon / **late start** (concept date passed, go-live still possible) / **missed go-live** / happening now / passed, instead of one catch-all "behind plan". Coming up shows the next deadline with a day count.
- The coming-up window includes ranges that began the previous year (e.g. the school Christmas break on 1 January).
- A saved campaign whose moment no longer exists is skipped with a warning instead of breaking the page, so it can still be removed.

### Examples and docs

- Committed example calendars in `examples/` (2026 moments; Fjellbrus demo with milestones) plus an XLSX plan, rebuilt by `scripts/generate_examples.py` and checked by a test. `.ics` files keep CRLF line endings via `.gitattributes`.
- macOS launcher `run_app.command`; Docker image verified (builds, passes its health check, runs as a non-root user).
- README screenshots captured with `scripts/take_screenshots.py`; deep links such as `?page=planner&moment=black_week`.
- The example `.ics` files were cross-checked with a second parser (vobject).

### Architecture

- UI-free, pip-installable package with a public API in `seasonsignal/__init__.py`; storage behind `storage.py`; a test fails if anything under `src/` imports streamlit.
