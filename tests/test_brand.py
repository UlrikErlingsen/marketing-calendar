"""The Signal brand: shared theme, family colour, display name, README layout and synced assets."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
UI = ROOT / "src" / "seasonsignal" / "ui"
OLD_COLOURS = ("#173c3a", "#d95b40", "#83d2b4", "#f2c66d", "#17322e", "#102c2a", "#f8f5ed")


def test_app_uses_the_shared_signal_theme_instead_of_pasted_styles():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "from seasonsignal.ui import signal_theme as sig" in app
    assert 'THEME = "season"' in app
    assert "st.set_page_config(**sig.page_config(THEME" in app
    assert "sig.apply(THEME)" in app and "sig.template(THEME)" in app
    for call in ("sig.sidebar_brand(", "sig.masthead(", "sig.hero(", "sig.cards(", "sig.note(", "sig.footer("):
        assert call in app, call
    assert "<style>" not in app and "unsafe_allow_html" not in app
    assert "sig.chart(THEME," in app and "st.plotly_chart" not in app  # Signal template + theme=None
    for colour in OLD_COLOURS:
        assert colour not in app.lower(), colour
    assert (UI / "__init__.py").exists()
    assert (UI / "assets" / "marks" / "seasonsignal-mark-64.png").exists()
    assert (UI / "assets" / "marks" / "seasonsignal-mark.svg").exists()


def test_theme_key_is_season_in_the_market_family():
    from seasonsignal.ui import signal_theme as sig

    app = sig.app("season")
    assert app["name"] == "Season Signal" and app["slug"] == "seasonsignal"
    assert app["family"] == "market" and app["fam"]["600"] == "#728157"
    assert sig.colorway("season")[0] == "#728157"


def test_streamlit_config_uses_the_family_colour():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'primaryColor = "#728157"' in config
    assert 'backgroundColor = "#f5ead8"' in config


def test_readme_follows_the_signal_template():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sections = [
        "## Read this first",
        "## Scope",
        "## Try the demo in two minutes",
        "## Data contract",
        "## Methods",
        "## Planning statuses",
        "## Exports",
        "## Run locally",
        "## Privacy",
        "## No install? Import the example calendars",
        "## Development",
        "## Where this fits in Signal",
        "## References",
        "## Originality and license",
    ]
    positions = [readme.find(f"\n{heading}\n") for heading in sections]
    assert all(position >= 0 for position in positions), dict(zip(sections, positions))
    assert positions == sorted(positions)
    assert readme.startswith('<p align="center">\n  <img src="assets/seasonsignal-banner.png"')
    assert "seasonsignal-banner.svg" not in readme
    assert "Signal-Market-728157" in readme  # family badge in the Market 600 colour
    assert "github.com/UlrikErlingsen/marketing-calendar/actions" in readme  # tests badge
    assert "**Season Signal**" in readme and "SeasonSignal" not in readme
    assert "Creator Signal" not in readme and "[Influence Signal]" in readme
    assert '<img src="assets/seasonsignal-mark-64.png"' in readme  # suite footer
    # Honesty statements survive the restructure.
    assert "Every rule is sourced or honestly labelled" in readme
    assert "represents no real company" in readme


def test_synced_brand_assets_replace_the_old_banner():
    assets = ROOT / "assets"
    for name in ("banner.png", "social.png", "mark.svg", "mark-32.png", "mark-64.png", "mark-512.png"):
        assert (assets / f"seasonsignal-{name}").exists(), name
    assert not (assets / "seasonsignal-banner.svg").exists()


def test_issue_templates_use_the_display_name_and_data_safety_wording():
    templates = ROOT / ".github" / "ISSUE_TEMPLATE"
    bug = (templates / "bug_report.yml").read_text(encoding="utf-8")
    feature = (templates / "feature_request.yml").read_text(encoding="utf-8")
    config = (templates / "config.yml").read_text(encoding="utf-8")
    assert "Season Signal" in bug and "Season Signal" in feature
    assert "Never attach confidential campaign plans" in bug
    assert "invented examples only" in feature
    assert "blank_issues_enabled: false" in config and "marketing-calendar/blob/main/SECURITY.md" in config
