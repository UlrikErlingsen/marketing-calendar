"""Signal Hub contract: importable UI entry point, Streamlit only under ui/, slug-namespaced state, and Hub mode
(SIGNAL_HUB=1): session-only campaigns, no files written or read, no network."""

import ast
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import urllib.request

import pytest
from streamlit.testing.v1 import AppTest

from seasonsignal import (
    PlanProblem,
    __version__,
    change_in_memory,
    load_library,
    memory_store,
    save_store,
    validate_campaign,
    Campaign,
)


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "seasonsignal"
UI = PACKAGE / "ui"
SYNCED = {"signal_theme.py", "signal_font.py"}
UI_ONLY_LIBRARIES = {"streamlit", "plotly"}
CORE_MODULES = (
    "seasonsignal", "seasonsignal.campaigns", "seasonsignal.errors", "seasonsignal.export", "seasonsignal.leadtimes",
    "seasonsignal.moments", "seasonsignal.planner", "seasonsignal.rules", "seasonsignal.storage",
)
# Every Streamlit call that creates a stateful widget (or a keyed chart) must pass an explicit key.
KEYED_CALLS = {
    "button", "checkbox", "data_editor", "date_input", "download_button", "file_uploader", "form_submit_button",
    "multiselect", "number_input", "chart", "plotly_chart", "radio", "selectbox", "slider", "text_area",
    "text_input", "toggle",
}
PAGES = [
    "Welcome",
    "1 · Planner",
    "2 · Coming up",
    "3 · My campaigns",
    "4 · Lead times",
    "5 · Export",
    "Sources & method",
]
RENDER_SCRIPT = """
from seasonsignal.ui import render

render()
"""


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _render() -> AppTest:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    return app


def _clean(app: AppTest) -> None:
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error, [error.value for error in app.error]


def _text(app: AppTest) -> str:
    return "\n".join(str(item.value) for item in [*app.markdown, *app.caption, *app.info])


@pytest.fixture
def standalone(tmp_path, monkeypatch):
    monkeypatch.delenv("SIGNAL_HUB", raising=False)
    monkeypatch.setenv("SEASONSIGNAL_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def hub(tmp_path, monkeypatch):
    """Hub mode in a temp working directory, with every per-user data location pointed at watched temp folders."""
    watched = {name: tmp_path / name for name in ("cwd", "home", "appdata", "data")}
    for folder in watched.values():
        folder.mkdir()
    monkeypatch.setenv("SIGNAL_HUB", "1")
    monkeypatch.chdir(watched["cwd"])
    monkeypatch.setenv("SEASONSIGNAL_DATA_DIR", str(watched["data"]))
    for name in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(name, str(watched["home"]))
    for name in ("APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(name, str(watched["appdata"]))

    # The UI must not even try to use the file store in the Hub.
    import seasonsignal.ui.app as ui_app

    def forbidden(*_args, **_kwargs):
        raise AssertionError("the file store was used in Hub mode")

    for name in ("load_store", "update_store", "default_store_path"):
        monkeypatch.setattr(ui_app, name, forbidden)
    return watched


LOOPBACK = {"127.0.0.1", "::1", "localhost", ""}


def _host(address) -> str:
    if isinstance(address, (tuple, list)) and address:
        return str(address[0])
    return str(address)  # AF_UNIX path or similar: local by definition


@pytest.fixture
def no_network(monkeypatch):
    """Every outbound (non-loopback) connection attempt is recorded and refused. Loopback stays open because the
    asyncio event loop on Windows talks to itself through a local socket pair."""
    calls = []

    def guard(name, original, address_of):
        def _guarded(*args, **kwargs):
            host = _host(address_of(args, kwargs))
            if host not in LOOPBACK and not host.startswith("127.") and "/" not in host and "\\" not in host:
                calls.append((name, host))
                raise OSError(f"network disabled in tests: {name} {host}")
            return original(*args, **kwargs)
        return _guarded

    monkeypatch.setattr(socket.socket, "connect", guard("socket.connect", socket.socket.connect, lambda a, k: a[1]))
    monkeypatch.setattr(
        socket.socket, "connect_ex", guard("socket.connect_ex", socket.socket.connect_ex, lambda a, k: a[1])
    )
    monkeypatch.setattr(
        socket, "create_connection", guard("socket.create_connection", socket.create_connection, lambda a, k: a[0])
    )
    monkeypatch.setattr(socket, "getaddrinfo", guard("socket.getaddrinfo", socket.getaddrinfo, lambda a, k: a[:1]))

    def refuse(name):
        def _refuse(*args, **_kwargs):
            calls.append((name, args[:1]))
            raise OSError(f"network disabled in tests: {name}")
        return _refuse

    monkeypatch.setattr(urllib.request, "urlopen", refuse("urllib.request.urlopen"))
    try:
        import requests
    except ImportError:
        pass
    else:
        monkeypatch.setattr(requests.Session, "request", refuse("requests.Session.request"))
    return calls


# ── Contract ──────────────────────────────────────────────────────────────────


def test_ui_entry_point_matches_the_hub_contract() -> None:
    from seasonsignal.ui import APP_INFO, render

    assert callable(render)
    assert APP_INFO == {
        "product": "Season Signal",
        "version": __version__,
        "repo": "marketing-calendar",
        "slug": "season",
    }


def test_only_the_ui_package_imports_streamlit_or_plotly() -> None:
    offenders = {
        str(path.relative_to(PACKAGE)): sorted(_imported_roots(path) & UI_ONLY_LIBRARIES)
        for path in PACKAGE.rglob("*.py")
        if UI not in path.parents and _imported_roots(path) & UI_ONLY_LIBRARIES
    }
    assert not offenders, offenders


def test_core_package_imports_without_streamlit_or_plotly() -> None:
    # A fresh interpreter, so modules already imported by other tests cannot hide a stray import.
    code = (
        f"import sys\nsys.path.insert(0, {str(ROOT / 'src')!r})\n"
        f"import importlib\nfor name in {CORE_MODULES!r}:\n    importlib.import_module(name)\n"
        "loaded = sorted(name for name in ('streamlit', 'plotly') if name in sys.modules)\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_render_never_sets_page_config_navigation_or_stops() -> None:
    for path in UI.glob("*.py"):
        if path.name in SYNCED:
            continue
        source = path.read_text(encoding="utf-8")
        for call in ("st.set_page_config(", "st.navigation(", "st.Page(", "st.stop("):
            assert call not in source, (path.name, call)
    assert not (ROOT / "pages").exists()  # one radio-driven app, no multipage folder to keep in sync


def test_render_runs_from_a_script_without_set_page_config(standalone) -> None:
    app = _render()

    _clean(app)
    assert app.sidebar.radio[0].key == "season:page"
    assert "season:store" in app.session_state and "store" not in app.session_state
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "MOMENTS → DEADLINES → CALENDAR" in body
    assert "NORWEGIAN MARKETING CALENDAR" in body
    assert f"Season Signal v{__version__}" in body


def test_render_works_from_the_packaged_files_alone(tmp_path: Path) -> None:
    # Signal Hub installs the release as a normal package: only src/seasonsignal/**/*.py and the declared package
    # data (moments/*.yaml, ui/assets/marks/*) exist there, so render() must not read examples/ or assets/.
    for path in PACKAGE.rglob("*"):
        relative = path.relative_to(PACKAGE)
        packaged = (
            path.suffix == ".py"
            or (relative.parent == Path("moments") and path.suffix == ".yaml")
            or relative.parent == Path("ui", "assets", "marks")
        )
        if path.is_file() and packaged and "__pycache__" not in relative.parts:
            target = tmp_path / "site" / "seasonsignal" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    site = str(tmp_path / "site")
    script = f"import sys\nsys.path.insert(0, {site!r})\nfrom seasonsignal.ui import render\nrender()\n"
    code = (
        f"import sys\nsys.path.insert(0, {site!r})\n"
        "from pathlib import Path\n"
        "from streamlit.testing.v1 import AppTest\n"
        "import seasonsignal\n"
        f"assert Path(seasonsignal.__file__).is_relative_to({site!r}), seasonsignal.__file__\n"
        "from seasonsignal.ui import signal_theme as sig\n"
        "assert Path(sig.page_config('season')['page_icon']).exists()\n"
        f"app = AppTest.from_string({script!r}, default_timeout=120)\n"
        "app.run()\n"
        "assert not app.exception, [error.value for error in app.exception]\n"
        "for page in ('1 · Planner', '3 · My campaigns', '5 · Export'):\n"
        "    app.sidebar.radio[0].set_value(page).run()\n"
        "    assert not app.exception, [error.value for error in app.exception]\n"
        "    assert not app.error, [error.value for error in app.error]\n"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=240,
        cwd=cwd,
        env={**os.environ, "SIGNAL_HUB": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert not any(cwd.iterdir())


@pytest.mark.parametrize("page", PAGES)
def test_every_widget_key_is_namespaced(hub, page: str) -> None:
    app = _render()
    app.sidebar.radio[0].set_value(page).run()

    _clean(app)
    widgets = [
        *app.radio, *app.selectbox, *app.checkbox, *app.button, *app.slider, *app.text_input, *app.text_area,
        *app.number_input, *app.multiselect, *app.toggle, *app.date_input,
    ]
    assert widgets
    unkeyed = [(type(widget).__name__, widget.label) for widget in widgets if widget.key is None]
    assert not unkeyed, unkeyed
    assert all(widget.key.startswith("season:") for widget in widgets), [w.key for w in widgets]
    state = list(app.session_state)
    assert state and all(str(key).startswith("season:") for key in state), state


def test_every_widget_call_passes_an_explicit_key() -> None:
    # Some widgets only appear after a click or inside a form; check the source too.
    tree = ast.parse((UI / "app.py").read_text(encoding="utf-8"))
    unkeyed = [
        (node.lineno, node.func.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in KEYED_CALLS
        and not any(keyword.arg == "key" for keyword in node.keywords)
    ]
    assert not unkeyed, unkeyed


def test_session_state_and_widget_keys_go_through_the_namespace_helper() -> None:
    source = (UI / "app.py").read_text(encoding="utf-8")
    state_keys = re.findall(r"session_state(?:\[|\.get\(|\.pop\()\s*([^,\])]+)", source)
    widget_keys = re.findall(r"\bkey=([^,)\n]+)", source)
    forms = re.findall(r"st\.form\(([^)\n]+)\)", source)
    assert state_keys and widget_keys and forms
    assert all(key.startswith("k(") for key in state_keys), state_keys
    assert all(key.startswith("k(") for key in widget_keys), widget_keys
    assert all(form.startswith("k(") for form in forms), forms
    assert 'NS = "season"' in source


# ── Hub mode ──────────────────────────────────────────────────────────────────


def test_the_network_guard_refuses_outbound_calls(no_network) -> None:
    with pytest.raises(OSError):
        urllib.request.urlopen("https://example.com")
    with pytest.raises(OSError):
        socket.create_connection(("192.0.2.1", 80), timeout=1)
    assert [name for name, _ in no_network] == ["urllib.request.urlopen", "socket.create_connection"]


@pytest.mark.parametrize("page", PAGES)
def test_hub_mode_renders_every_page_without_files_or_network(hub, no_network, page: str) -> None:
    app = _render()
    app.sidebar.radio[0].set_value(page).run()

    _clean(app)
    assert not no_network, no_network
    assert app.session_state["season:store"].path is None
    assert "Signal Hub · campaigns last for this session only" in "\n".join(str(c.value) for c in app.sidebar.caption)
    if page in ("Welcome", "3 · My campaigns", "4 · Lead times"):
        assert "Saving is off in Signal Hub" in _text(app)
    if page == "3 · My campaigns":
        assert "Fjellbrus" in _text(app) or any("Fjellbrus" in str(e.label) for e in app.expander)
        assert not any(str(c.value).startswith("File:") for c in app.caption)
    for folder in hub.values():
        assert not any(folder.iterdir()), (folder, list(folder.iterdir()))


def test_hub_mode_keeps_campaigns_and_lead_times_in_the_session_only(hub, no_network) -> None:
    app = _render()
    app.sidebar.radio[0].set_value("3 · My campaigns").run()
    app.text_input(key="season:add-campaign-0-name").input("Hub-only summer push").run()
    next(b for b in app.button if b.label == "Add campaign").click().run()
    _clean(app)
    names = [c.name for c in app.session_state["season:store"].campaigns]
    assert "Hub-only summer push" in names and len(names) == 4

    next(b for b in app.button if b.label == "Remove fictional demo campaigns").click().run()
    _clean(app)
    assert [c.name for c in app.session_state["season:store"].campaigns] == ["Hub-only summer push"]

    app.sidebar.radio[0].set_value("4 · Lead times").run()
    next(b for b in app.button if b.label == "Save lead times").click().run()
    next(b for b in app.button if b.label == "Reset to defaults").click().run()
    _clean(app)
    assert app.session_state["season:store"].lead_times["food"]["concept"] == 16

    app.sidebar.radio[0].set_value("5 · Export").run()  # .ics and XLSX are built in memory
    _clean(app)

    assert not no_network, no_network
    for folder in hub.values():
        assert not any(folder.iterdir()), (folder, list(folder.iterdir()))
    # A new browser session starts from the fictional demo again.
    fresh = _render()
    assert [c.fictional for c in fresh.session_state["season:store"].campaigns] == [True, True, True]


def test_hub_mode_never_reads_an_existing_local_save_file(tmp_path, monkeypatch) -> None:
    data = tmp_path / "data"
    data.mkdir()
    saved = data / "seasonsignal.json"
    saved.write_text(json.dumps({
        "version": 1,
        "lead_times": {"food": {"concept": 30, "creative": 10, "media": 6, "live": 1}},
        "campaigns": [{"id": "x", "name": "Somebody's real plan", "moment_id": "black_week", "year": 2026,
                       "category": "food"}],
    }), encoding="utf-8")
    before = (saved.read_bytes(), saved.stat().st_mtime_ns)
    monkeypatch.setenv("SEASONSIGNAL_DATA_DIR", str(data))
    monkeypatch.setenv("SIGNAL_HUB", "1")

    app = _render()
    app.sidebar.radio[0].set_value("3 · My campaigns").run()
    _clean(app)
    store = app.session_state["season:store"]
    assert "Somebody's real plan" not in [c.name for c in store.campaigns]
    assert store.lead_times["food"]["concept"] == 16
    assert (saved.read_bytes(), saved.stat().st_mtime_ns) == before
    assert sorted(p.name for p in data.iterdir()) == ["seasonsignal.json"]


def test_hub_mode_ignores_deep_links_because_the_hub_owns_the_url(hub) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.query_params["page"] = "planner"
    app.run()
    _clean(app)
    assert app.sidebar.radio[0].value == "Welcome"


def test_memory_store_is_never_saved_and_changes_are_copies() -> None:
    library = load_library()
    store = memory_store(demo_year=2026)
    assert store.path is None and not store.saved and len(store.campaigns) == 3
    with pytest.raises(PlanProblem):
        save_store(store)

    campaign = validate_campaign(Campaign(name="x", moment_id="black_week", year=2026, category="food"), library)
    updated = change_in_memory(store, lambda s: s.campaigns.append(campaign))
    assert len(updated.campaigns) == 4 and len(store.campaigns) == 3

    def bad(s):
        s.lead_times["food"]["concept"] = -1

    with pytest.raises(PlanProblem):
        change_in_memory(store, bad)
    assert store.lead_times["food"]["concept"] == 16
