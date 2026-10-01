# Contributing

Season Signal's central boundary: **every date is computed from a rule, and every rule is sourced or honestly labelled as a convention.**

When you add or change a moment in `src/seasonsignal/moments/no.yaml`:

- Use a rule (`fixed`, `easter`, `nth_weekday`, `weekday_on_or_after`, `iso_week`, `relative`) — never a date typed in for one year.
- Set `basis`: `official` (law or owning body, with its URL), `tradition` (documented by an authoritative reference such as SNL), `observed` (set locally — show a range and add verified `variants`), or `convention` (no owner; explain why in `notes`).
- If the date varies by kommune or fylke, set `varies` and give a range. Regional `variants` need their own source and the school years you checked in `verified`.
- Add a test with known dates for at least two years.

Keep the architecture rule for Signal Hub: logic, models and storage live in `src/seasonsignal/` and never import streamlit, except `src/seasonsignal/ui/` (the synced Signal theme and its marks); the app lives in `app.py`; saved state goes through `storage.py` only. Never edit the synced theme files (`src/seasonsignal/ui/signal_theme.py`, `src/seasonsignal/ui/assets/marks/*`, `.streamlit/config.toml`, `assets/seasonsignal-*.png|svg`); change them in Signal Hub's `signal-theme/` and re-sync.

Before submitting a change:

```bash
python -m pytest
python -m ruff check .
python -m build
```

Use fictional brands in examples and tests.
