from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

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


@pytest.mark.parametrize("year", [2025, 2030, 2035])
@pytest.mark.parametrize("page", ["1 · Planner", "5 · Export"])
def test_year_selector_and_region(page, year):
    app = _app()
    app.sidebar.radio[0].set_value(page).run()
    app.sidebar.selectbox(key="year").set_value(year).run()
    app.sidebar.selectbox(key="region").set_value("oslo").run()
    app.sidebar.checkbox(key="show_all").check().run()
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error, [error.value for error in app.error]


def test_shell_demo_and_boundaries():
    app = _app()
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "MOMENTS → DEADLINES → CALENDAR" in body
    assert "Part of the Signal suite" in body and "AGPL-3.0-or-later" in body
    assert "Fjellbrus is a fictional" in body


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
