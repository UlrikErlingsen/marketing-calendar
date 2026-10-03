# Changelog

## [1.1.0] - 2026-10-03

### Larger datasets

- Larger datasets: Season Signal has no built-in data limits. The plan is typed in, not uploaded, so there is no upload path and nothing to cap, locally or in a public demo (`SIGNAL_PUBLIC=1`); a new test keeps it that way (an uploader added later must bring a limits module that is unbounded locally).
- Launchers accept `SEASONSIGNAL_MAX_UPLOAD_MB` (default 10000) for `--server.maxUploadSize`; before, they passed no cap and relied on the config file. The Dockerfile sets `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000`. Signal Hub mode is unchanged.
- New `tests/test_upload_cap.py`: config, launchers and Docker agree on 10,000 MB, Docker sets it by environment only, and the package has no file uploader.
- The example calendars in `examples/` are regenerated (`PRODID` carries the version; event titles are now English).
- Tests: the add-campaign UI tests type the name and submit the form in one AppTest run; Streamlit 1.65 drops uncommitted form values on a rerun without submit, which made them fail intermittently.

### English

- All app text is in English. Moments show their English name with the Norwegian name in brackets (`Moment.display_name`, e.g. "Constitution Day (17. mai — Grunnlovsdagen)") on every screen, in the planner, campaign and sources tables, the XLSX and the ICS export ("varierer lokalt" is now "varies locally"); the separate "Moment (en)" column is gone. Regions read "All of Norway" and "Oslo municipality (kommune)" etc., moment notes and screen texts gloss Norwegian terms on first use (the Public Holidays Act (helligdagsfredloven), school calendar (skolerute), municipality (kommune)), and the README and CONTRIBUTING follow. The demo keeps its Norwegian campaign names, with a note that the tool is built for the Norwegian market.

### Suite

- Suite: Rival, Reach, Learn and Blueprint Signal added to the suite table; the synced Signal config sets `maxUploadSize = 10000`.

## [1.0.0] - 2026-10-02

First release of **Season Signal**, the Norwegian marketing calendar in the Signal suite.

### Signal Hub

- `seasonsignal.ui` exposes `APP_INFO` and `render()`, which draws the whole app (theme, sidebar with a namespaced page radio, masthead, page, footer) without `st.set_page_config`, `st.navigation` or `st.stop`. The app body moved from `app.py` to `seasonsignal.ui.app`; `app.py` is a thin standalone wrapper.
- Every session-state, widget and form key is namespaced `season:` through one `k()` helper.
- Hub mode (`SIGNAL_HUB=1`): campaigns and lead times live in the browser session only, seeded with the fictional Fjellbrus demo (`memory_store`, `change_in_memory`); the local save file is never read or written, `?page=` deep links are ignored because the Hub owns the URL, and the Welcome, My campaigns and Lead times pages say that saving is off. `.ics` and XLSX remain in-memory downloads.
- "Today" is computed on every run, so a long-running process never keeps the day it started on.
- Streamlit and Plotly are in the `ui` extra (previously `app`); `requirements.txt` still installs everything.
- `tests/test_hub_contract.py`: the entry point, the Streamlit/Plotly import guard, a fresh-interpreter core import, no page config or navigation in `ui/`, a render from the packaged files alone, namespaced keys on every page, and Hub mode with no files written or read (temporary working, home and app-data folders stay empty; a planted save file is ignored and untouched) and no outbound network calls.
- `CITATION.cff`.

### Signal brand refresh

- The app uses the shared Signal theme (`seasonsignal.ui.signal_theme`, Market family): cream ground, dark warm sidebar, Figtree, the Season Signal mark as favicon and in the sidebar and masthead. The pasted CSS, hand-made lockup, masthead, hero, cards, notes and footer are gone; the app's words and pages are unchanged.
- The timeline uses the Signal Plotly template and colorway for the four moment kinds; the "today" line uses the neutral reference colour.
- Display name **Season Signal** (with a space) in the app, exports (calendar name, milestone descriptions, XLSX About sheet), launchers and docs. Package, environment-variable and file names are unchanged. Example exports regenerated.
- README follows the Signal README template: new banner (`assets/seasonsignal-banner.png`), family badges, Scope, Data contract, Methods, Planning statuses, "Where this fits in Signal" and the suite footer. The old `assets/seasonsignal-banner.svg` is removed.
- Bug-report and feature-request issue templates.
- The architecture rule now reads "no Streamlit under `src/seasonsignal/` except `src/seasonsignal/ui/`"; the guard test allows only `ui/`. The marks ship as package data.
- `plotly` widened to `>=5.18,<8` so Season Signal installs next to the other Signal apps.
- Figtree is embedded with the theme (`seasonsignal.ui.signal_font`, OFL licence included); the app no longer requests Google Fonts.
- README screenshots re-taken in the Signal theme; `scripts/take_screenshots.py` waits for the new `.sg-foot` footer.

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

### Fixes from an independent review

- A malformed or older save file no longer crashes the app: older files missing a milestone get the default per milestone, and a broken file shows its path and how to recover instead of a traceback.
- Saves re-read the file and apply the change under a lock (`storage.update_store`), with a unique temp file and a retry for OneDrive/virus-scanner locks — two browser tabs can no longer overwrite each other's campaigns.
- "Reset to defaults" now really resets the lead-time editor.
- `.ics` events carry SEQUENCE and LAST-MODIFIED; milestone UIDs include the planning category, so plans for different categories never collide. The app no longer promises that re-importing updates events.
- The planner year includes ranges that began the previous year (1–3 January of the school Christmas break).
- A failed campaign form keeps what you typed and the rest of the page.

### Examples and docs

- Committed example calendars in `examples/` (2026 moments; Fjellbrus demo with milestones) plus an XLSX plan, rebuilt by `scripts/generate_examples.py` and checked by a test. `.ics` files keep CRLF line endings via `.gitattributes`.
- macOS launcher `run_app.command`; Docker image verified (builds, passes its health check, runs as a non-root user).
- README screenshots captured with `scripts/take_screenshots.py`; deep links such as `?page=planner&moment=black_week`.
- The example `.ics` files were cross-checked with a second parser (vobject).

### Architecture

- UI-free, pip-installable package with a public API in `seasonsignal/__init__.py`; storage behind `storage.py`; a test fails if anything under `src/` outside `seasonsignal.ui` imports streamlit.
