from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seasonsignal import __version__

ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
PAGES = [
    "Welcome",
    "1 · Planner",
    "2 · Coming up",
    "3 · My campaigns",
    "4 · Lead times",
    "5 · Export",
    "Sources & method",
]


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("SEASONSIGNAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SIGNAL_HUB", raising=False)  # these tests cover the standalone app
    return tmp_path


def _app() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    return app


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_with_fictional_demo(page):
    app = _app()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error, [error.value for error in app.error]
    assert "norwegian marketing calendar" in " ".join(str(c.value).lower() for c in app.sidebar.caption)


@pytest.mark.parametrize("year,region", [(2025, "oslo"), (2030, "bergen"), (2035, "trondheim")])
@pytest.mark.parametrize("page", ["1 · Planner", "5 · Export"])
def test_year_selector_and_region(page, year, region):
    app = _app()
    app.sidebar.radio[0].set_value(page).run()
    app.sidebar.selectbox(key="season:year").set_value(year).run()
    app.sidebar.selectbox(key="season:region").set_value(region).run()
    app.sidebar.checkbox(key="season:show_all").check().run()
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error, [error.value for error in app.error]


def test_shell_demo_and_boundaries():
    app = _app()
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "MOMENTS → DEADLINES → CALENDAR" in body
    assert "Part of the Signal suite" in body and "AGPL-3.0-or-later" in body
    assert "Fjellbrus is a fictional" in body
    # The shared Signal shell: masthead, hero, cards, notes and footer come from signal_theme.
    assert "sg-mast" in body and "sg-hero" in body and "sg-card" in body
    assert "sg-note boundary" in body and "sg-foot" in body
    assert f"Season Signal v{__version__}" in body
    sidebar = "\n".join(str(item.value) for item in app.sidebar.markdown)
    assert "sg-side" in sidebar and "The Norwegian marketing year, worked backwards." in sidebar


def test_adding_a_campaign_saves_locally(isolated_store):
    app = _app()
    app.sidebar.radio[0].set_value("3 · My campaigns").run()
    app.text_input[0].input("Russ-safe summer").run()
    next(b for b in app.button if b.label == "Add campaign").click().run()
    assert not app.exception, [error.value for error in app.exception]
    saved = (isolated_store / "seasonsignal.json").read_text(encoding="utf-8")
    assert "Russ-safe summer" in saved and "Fjellbrus" in saved


def test_deep_link_opens_planner_on_a_moment():
    app = AppTest.from_file(APP, default_timeout=120)
    app.query_params["page"] = "planner"
    app.query_params["moment"] = "black_week"
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].value == "1 · Planner"
    assert any("Black Week" in str(item.value) for item in app.markdown if str(item.value).startswith("###"))


def test_campaign_for_unknown_moment_does_not_break_pages(isolated_store):
    import json

    (isolated_store / "seasonsignal.json").write_text(json.dumps({
        "version": 1,
        "lead_times": {},
        "campaigns": [{"id": "old", "name": "Renamed moment", "moment_id": "gone", "year": 2026, "category": "food"}],
    }), encoding="utf-8")
    for page in ("3 · My campaigns", "5 · Export"):
        app = _app()
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, [error.value for error in app.exception]
        assert not app.error, [error.value for error in app.error]
        if page == "3 · My campaigns":
            assert any("Renamed moment" in str(w.value) for w in app.warning)
            assert any(b.label == "Remove campaign" for b in app.button)  # it can still be removed


def test_planner_year_includes_christmas_break_tail_and_bad_files_are_reported(isolated_store):
    app = AppTest.from_file(APP, default_timeout=120)
    app.query_params["page"] = "planner"
    app.run()
    app.sidebar.selectbox(key="season:year").set_value(2027).run()
    app.sidebar.checkbox(key="season:show_all").check().run()
    assert not app.exception, [error.value for error in app.exception]

    (isolated_store / "seasonsignal.json").write_text('{"version": 1, "campaigns": [{"name": "x"}]}', encoding="utf-8")
    broken = _app()
    assert not broken.exception, [error.value for error in broken.exception]
    assert any("malformed" in str(e.value) for e in broken.error)


def test_older_file_missing_a_milestone_still_loads(isolated_store):
    (isolated_store / "seasonsignal.json").write_text(
        '{"version": 1, "lead_times": {"food": {"concept": 20}}, "campaigns": []}', encoding="utf-8"
    )
    app = _app()
    app.sidebar.radio[0].set_value("4 · Lead times").run()
    assert not app.exception and not app.error
    assert app.session_state["season:store"].lead_times["food"] == {"concept": 20, "creative": 10, "media": 6, "live": 1}


def test_failed_campaign_form_keeps_page_and_input():
    app = _app()
    app.sidebar.radio[0].set_value("3 · My campaigns").run()
    next(b for b in app.button if b.label == "Add campaign").click().run()  # empty name
    assert any("name" in str(e.value).lower() for e in app.error)
    assert any(b.label == "Remove campaign" for b in app.button)  # rest of the page still renders


def test_two_sessions_do_not_overwrite_each_other(isolated_store):
    first, second = _app(), _app()
    for app, name in ((first, "From tab one"), (second, "From tab two")):
        app.sidebar.radio[0].set_value("3 · My campaigns").run()
        app.text_input[0].input(name).run()
        next(b for b in app.button if b.label == "Add campaign").click().run()
        assert not app.exception, [error.value for error in app.exception]
    saved = (isolated_store / "seasonsignal.json").read_text(encoding="utf-8")
    assert "From tab one" in saved and "From tab two" in saved


def test_reset_lead_times_resets_the_editor(isolated_store):
    (isolated_store / "seasonsignal.json").write_text(
        '{"version": 1, "lead_times": {"food": {"concept": 30, "creative": 10, "media": 6, "live": 1}}, '
        '"campaigns": []}', encoding="utf-8"
    )
    app = _app()
    app.sidebar.radio[0].set_value("4 · Lead times").run()
    next(b for b in app.button if b.label == "Reset to defaults").click().run()
    assert not app.exception
    assert app.session_state["season:store"].lead_times["food"]["concept"] == 16
    assert not app.session_state["season:lead-time-editor"]["edited_rows"]  # no stale edits re-applied
