"""SeasonSignal Streamlit application."""

from __future__ import annotations

import os

# Keep Arrow serialization stable on macOS. This must be set before Streamlit imports Arrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import base64
import sys
import traceback
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from seasonsignal import (
    DEFAULT_LEAD_TIMES,
    MAX_YEAR,
    MILESTONES,
    MIN_YEAR,
    Campaign,
    PlanProblem,
    __version__,
    about_frame,
    build_ics,
    build_xlsx,
    campaign_items,
    campaigns_frame,
    friendly_message,
    lead_times_frame,
    load_library,
    default_store_path,
    load_store,
    milestones_frame,
    moment_items,
    moments_frame,
    plan_campaign,
    plan_moments,
    planning_status,
    select_occurrences,
    update_store,
    validate_campaign,
    validate_lead_times,
)

KIND_COLORS = {
    "Public holiday": "#173C3A",
    "Retail moment": "#D95B40",
    "Season & holidays": "#83D2B4",
    "Cultural moment": "#F2C66D",
}
STATUS_ICONS = {
    "on track": "🟢 on track",
    "start soon": "🟡 start soon",
    "late start": "🟠 late start",
    "missed go-live": "🔴 missed go-live",
    "happening now": "🔵 happening now",
    "passed": "⚪ passed",
}
mark_path = ROOT / "assets" / "seasonsignal-mark.svg"
MARK_URI = (
    "data:image/svg+xml;base64," + base64.b64encode(mark_path.read_bytes()).decode("ascii")
    if mark_path.exists()
    else ""
)


st.set_page_config(page_title="SeasonSignal | Norwegian marketing calendar", page_icon="◉", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --ps-ink:#17322e; --ps-deep:#102c2a; --ps-teal:#173c3a;
        --ps-coral:#d95b40; --ps-mint:#83d2b4; --ps-gold:#f2c66d;
        --ps-paper:#f8f5ed; --ps-line:rgba(23,50,46,.14);
    }
    [data-testid="stAppViewContainer"] {
        background:radial-gradient(circle at 94% 2%,rgba(131,210,180,.17),transparent 28rem),
                   radial-gradient(circle at 3% 93%,rgba(242,198,109,.14),transparent 25rem),
                   linear-gradient(180deg,#fbf9f3 0%,var(--ps-paper) 100%);
    }
    [data-testid="stHeader"] { background:rgba(248,245,237,.78); }
    [data-testid="stSidebar"] { background:linear-gradient(165deg,#173c3a 0%,#102c2a 65%,#0c2422 100%); }
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span { color:#f8f5ed; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#b9cbc5; }
    [data-testid="stSidebar"] [data-baseweb="select"] span { color:#17322e; }
    [data-testid="stSidebar"] button {
        background:rgba(255,255,255,.08); color:#f8f5ed !important; border-color:rgba(255,255,255,.23);
    }
    [data-testid="stSidebar"] button:hover { background:rgba(242,198,109,.14); border-color:rgba(242,198,109,.48); }
    [data-testid="stSidebar"] button * { color:#f8f5ed !important; }
    .block-container { max-width:1240px; padding-top:4.4rem; padding-bottom:4rem; }
    h1,h2,h3 { color:var(--ps-ink); letter-spacing:-.025em; }
    a { color:#9b3e2b; }
    [data-testid="stMetric"] {
        background:rgba(255,255,255,.75); border:1px solid var(--ps-line); border-radius:16px;
        padding:1rem 1.05rem; box-shadow:0 8px 28px rgba(23,50,46,.045);
    }
    [data-testid="stMetricValue"] { color:var(--ps-ink); font-size:clamp(1.25rem,2.1vw,1.7rem); }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] > button {
        background:linear-gradient(135deg,#e26748,#c94c34); color:white; border:0;
        box-shadow:0 8px 20px rgba(217,91,64,.22); font-weight:750;
    }
    .stButton > button[kind="primary"]:hover { background:linear-gradient(135deg,#c94c34,#b63f2b); color:white; }
    button:focus-visible,a:focus-visible,input:focus-visible,[role="radio"]:focus-visible {
        outline:3px solid #f2c66d !important; outline-offset:2px;
    }
    [data-testid="stExpander"],[data-testid="stAlert"],[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
    .ps-lockup { display:flex; align-items:center; gap:.65rem; }
    .ps-mark { width:38px; height:38px; }
    .ps-name { color:white; font-size:1.28rem; line-height:1; font-weight:850; letter-spacing:-.04em; }
    .ps-name span { color:#f2c66d !important; }
    .ps-tag { margin:.55rem 0 0 !important; color:#b9cbc5 !important; font-size:.77rem; line-height:1.4; }
    .ps-masthead {
        display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.72rem 1rem .72rem .78rem;
        margin-bottom:1.35rem; background:rgba(255,255,255,.65); border:1px solid var(--ps-line);
        border-radius:18px; box-shadow:0 10px 36px rgba(23,50,46,.05);
    }
    .ps-masthead .ps-mark { width:48px; height:48px; }
    .ps-wordmark { color:var(--ps-ink); font-weight:850; letter-spacing:-.045em; font-size:1.55rem; line-height:1; }
    .ps-wordmark span { color:var(--ps-coral); }
    .ps-kicker { margin-top:.32rem; color:#59716c; font-size:.67rem; font-weight:800; letter-spacing:.13em; }
    .ps-promise { color:#47645e; font-size:.78rem; font-weight:700; white-space:nowrap; }
    .ps-promise span { color:var(--ps-coral); padding:0 .3rem; }
    .ps-hero {
        position:relative; overflow:hidden; padding:clamp(1.7rem,4vw,3.4rem); margin-bottom:1.3rem;
        background:linear-gradient(135deg,#173c3a 0%,#102c2a 75%); border-radius:26px;
        box-shadow:0 18px 50px rgba(23,50,46,.17);
    }
    .ps-hero:after {
        content:""; position:absolute; width:330px; height:330px; right:-105px; top:-148px;
        border-radius:50%; border:56px solid rgba(131,210,180,.12);
    }
    .ps-eyebrow { color:#83d2b4; font-size:.72rem; font-weight:850; letter-spacing:.16em; }
    .ps-hero h1 { color:white; font-size:clamp(2.1rem,4.6vw,4.3rem); line-height:.98; margin:.75rem 0 1rem; max-width:980px; }
    .ps-hero h1 em { color:#f2c66d; font-style:normal; }
    .ps-hero p { color:#d7e3df; font-size:1.06rem; line-height:1.6; max-width:820px; }
    .ps-pills { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.15rem; }
    .ps-pill {
        padding:.4rem .72rem; border:1px solid rgba(255,255,255,.16); border-radius:999px;
        color:#f8f5ed; font-size:.78rem; font-weight:700; background:rgba(255,255,255,.055);
    }
    .ps-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; margin:1.2rem 0 1.5rem; }
    .ps-card {
        height:100%; padding:1.2rem 1.2rem 1rem; background:rgba(255,255,255,.68);
        border:1px solid var(--ps-line); border-radius:18px;
    }
    .ps-card b { color:var(--ps-coral); font-size:.72rem; letter-spacing:.12em; }
    .ps-card h3 { margin:.4rem 0 .5rem; }
    .ps-card p { color:#59716c; font-size:.9rem; line-height:1.55; }
    .pulse-kicker {font-size:.72rem;font-weight:800;letter-spacing:.14em;color:var(--ps-coral);text-transform:uppercase;}
    .pulse-title {font-size:2.15rem;line-height:1.08;font-weight:850;color:var(--ps-ink);margin:.2rem 0 .6rem;}
    .pulse-subtitle {font-size:1.02rem;color:#526a65;max-width:850px;margin-bottom:1.2rem;line-height:1.55;}
    .boundary {border-left:4px solid var(--ps-mint);background:rgba(255,255,255,.62);border-radius:0 14px 14px 0;padding:1rem 1.1rem;color:#47645e;}
    .warning-box {border-left:4px solid var(--ps-gold);background:rgba(242,198,109,.17);border-radius:0 14px 14px 0;padding:1rem 1.1rem;color:#604b1f;}
    .small-note {font-size:.86rem;color:#617670;}
    .ps-footer { margin-top:3.2rem; padding-top:1rem; border-top:1px solid var(--ps-line); color:#617670; font-size:.76rem; text-align:center; }
    .ps-footer span { color:var(--ps-coral); padding:0 .38rem; }
    @media (max-width:1050px) { .ps-grid{grid-template-columns:1fr} }
    @media (max-width:760px) { .ps-promise{display:none}.ps-hero{border-radius:20px}.block-container{padding-top:3.5rem} }
    @media (prefers-reduced-motion:reduce) { * { scroll-behavior:auto !important; transition:none !important; } }
    </style>
    """,
    unsafe_allow_html=True,
)


LIBRARY = load_library()
TODAY = date.today()
CATEGORY_KEYS = list(LIBRARY.categories)
REGION_KEYS = list(LIBRARY.regions)


def _default_year() -> int:
    return min(max(TODAY.year, MIN_YEAR), MAX_YEAR)


def _ensure_state() -> None:
    # Read the (small) file on every run, so a second browser tab never works from a stale copy.
    try:
        st.session_state["store"] = load_store(demo_year=_default_year())
    except PlanProblem as exc:
        show_error(exc)
        st.caption(f"Saved plans live in {default_store_path()}. Fix or move that file, then reload the page.")
        st.stop()


def _store():
    return st.session_state["store"]


def _persist(message: str, change) -> None:
    """Apply ``change`` to the freshly re-read store and save it (see storage.update_store)."""
    store = update_store(change, demo_year=_default_year())
    st.session_state["store"] = store
    st.toast(f"{message} Saved to {store.path.name}.")


def _form_key(name: str) -> str:
    # Forms keep their input when validation fails; a new key after a successful submit clears them.
    return f"{name}-{st.session_state.get('form_version', 0)}"


def _form_done() -> None:
    st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1


def show_error(exc: Exception) -> None:
    """Render a useful error while keeping tracebacks opt-in."""
    st.error(friendly_message(exc))
    if not isinstance(exc, (PlanProblem, ValueError)) and os.getenv("SEASONSIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def masthead() -> None:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f"""
        <div class="ps-masthead">
          <div class="ps-lockup">{mark}<div><div class="ps-wordmark">Season<span>Signal</span></div>
          <div class="ps-kicker">MOMENTS → DEADLINES → CALENDAR</div></div></div>
          <div class="ps-promise">Computed dates <span>◆</span> Sourced rules <span>◆</span> Local plans</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        f'<div class="ps-footer">SeasonSignal v{__version__} <span>◆</span> dates computed, sources cited '
        '<span>◆</span> Part of the Signal suite <span>◆</span> AGPL-3.0-or-later</div>',
        unsafe_allow_html=True,
    )


def _header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="pulse-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _fmt(day: date) -> str:
    return f"{day:%a %d.%m.%Y}"


def _span(start: date, end: date) -> str:
    return _fmt(start) if start == end else f"{_fmt(start)} – {_fmt(end)}"


def _selection():
    """The sidebar choices every page shares."""
    return (
        st.session_state["year"],
        st.session_state["category"],
        st.session_state["region"],
        st.session_state["show_all"],
    )


def _planned(year: int, category: str, region: str, show_all: bool):
    # The calendar year, including ranges that began the year before (e.g. the school Christmas break).
    year_view = LIBRARY.window(date(year, 1, 1), 12, region)
    occurrences = select_occurrences(LIBRARY, year_view, category, include_all=show_all)
    return plan_moments(LIBRARY, occurrences, _store().lead_times, category)


def _campaign_plans(year: int | None = None, *, warn: bool = False):
    """Plans for saved campaigns. A campaign that no longer fits the library (e.g. its moment was renamed) is
    skipped — optionally with a warning — so it can still be removed on the My campaigns page."""
    store = _store()
    plans = []
    for campaign in store.campaigns:
        if year is not None and campaign.year != year:
            continue
        try:
            plans.append(plan_campaign(campaign, LIBRARY, store.lead_times))
        except PlanProblem as exc:
            if warn:
                st.warning(f"“{campaign.name}” cannot be planned and is left out: {exc} Remove it below.")
    return plans


DATE_COLUMNS = {
    name: st.column_config.DateColumn(name, format="DD.MM.YYYY")
    for name in ("Start", "End", *(label for _key, label in MILESTONES))
}
MILESTONE_ICONS = {"on track": "🟢 on track", "due soon": "🟡 due soon", "overdue": "🔴 overdue"}


def _milestone_table(milestones) -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "Milestone": m.label,
                "Weeks": f"−{m.weeks_before}",
                "Due": f"{m.due:%a %d.%m.%y}",
                "Status": MILESTONE_ICONS[m.status(TODAY)],
                "Moved": f"from {m.moved_from:%d.%m} (weekend/holiday)" if m.moved_from else "",
            }
            for m in milestones
        ]
    )
    return frame if frame["Moved"].any() else frame.drop(columns=["Moved"])


def timeline_figure(frame: pd.DataFrame, year: int) -> go.Figure:
    """Ranges as bars, single days as diamonds (a one-day bar is too thin to see or click)."""
    frame = frame.sort_values(["Start", "End"]).reset_index(drop=True)
    varies = frame["Varies locally"].eq("Yes — range")
    frame["label"] = [f"{name} ⇢" if flag else name for name, flag in zip(frame["Moment"], varies)]
    single = frame["Start"].eq(frame["End"])
    fig = go.Figure()
    for kind, color in KIND_COLORS.items():
        ranges = frame[frame["Kind"].eq(kind) & ~single]
        days = frame[frame["Kind"].eq(kind) & single]
        if not ranges.empty:
            fig.add_trace(go.Bar(
                name=kind, legendgroup=kind, orientation="h", y=ranges["label"],
                base=pd.to_datetime(ranges["Start"]),
                x=[((end - start).days + 1) * 86_400_000 for start, end in zip(ranges["Start"], ranges["End"])],
                marker=dict(color=color, line=dict(color="rgba(23,50,46,.35)", width=1)),
                customdata=ranges[["id"]].to_numpy(),
                text=[_span(a, b) for a, b in zip(ranges["Start"], ranges["End"])],
                textposition="none", hovertemplate="<b>%{y}</b><br>%{text}<extra>" + kind + "</extra>",
            ))
        if not days.empty:
            fig.add_trace(go.Scatter(
                name=kind, legendgroup=kind, showlegend=ranges.empty, mode="markers", y=days["label"],
                x=[datetime.combine(d, time(12)) for d in days["Start"]],
                marker=dict(symbol="diamond", size=12, color=color, line=dict(color="rgba(23,50,46,.5)", width=1)),
                customdata=days[["id"]].to_numpy(), text=[_fmt(d) for d in days["Start"]],
                hovertemplate="<b>%{y}</b><br>%{text}<extra>" + kind + "</extra>",
            ))
    fig.update_yaxes(categoryorder="array", categoryarray=list(reversed(frame["label"])), title=None)
    fig.update_xaxes(
        type="date", range=[f"{year - 1}-12-27", f"{year + 1}-01-08"], dtick="M1", tickformat="%b", title=None,
        showgrid=True, gridcolor="rgba(23,50,46,.08)",
    )
    if date(year, 1, 1) <= TODAY <= date(year, 12, 31):
        fig.add_vline(x=pd.Timestamp(TODAY).value / 1e6, line=dict(color="#D95B40", width=2, dash="dot"))
        fig.add_annotation(x=pd.Timestamp(TODAY), y=1.02, yref="paper", text="today", showarrow=False,
                           font=dict(color="#D95B40", size=11))
    fig.update_layout(
        barmode="overlay", height=max(360, 24 * len(frame) + 110), margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.06, x=0, title=None), plot_bgcolor="rgba(255,255,255,.6)",
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#17322E"), bargap=0.25, clickmode="event+select",
    )
    return fig


def moment_details(moment_id: str, year: int, category: str, region: str) -> None:
    occ = LIBRARY.resolve(moment_id, year, region)
    item = plan_moments(LIBRARY, [occ], _store().lead_times, category)[0]
    moment = occ.moment
    with st.container(border=True):
        st.markdown(f"### {moment.name_nb}")
        st.caption(moment.name_en)
        left, right = st.columns([1.1, 1])
        with left:
            st.markdown(f"**When:** {_span(occ.start, occ.end)}")
            if occ.varies_here:
                st.markdown(
                    '<div class="warning-box">Set locally by each kommune/fylkeskommune — this is the national '
                    "<strong>range</strong>, not a date. Pick a region with a verified rule or check the local "
                    "skolerute.</div>",
                    unsafe_allow_html=True,
                )
            elif occ.regional:
                st.caption(f"Regional rule for {LIBRARY.regions[region]} (verified against the source below).")
            st.write(moment.notes)
            st.markdown(f"**Basis:** {moment.basis} · **Source:** [{occ.source}]({occ.source})")
            st.caption("Categories: " + ", ".join(LIBRARY.category_label(t) for t in moment.tags))
        with right:
            st.markdown(f"**Plan-back for {LIBRARY.category_label(category)}** · {STATUS_ICONS[planning_status(item, TODAY)]}")
            st.dataframe(_milestone_table(item.milestones), hide_index=True, use_container_width=True)
            st.caption("Milestones landing on a weekend or public holiday move to the previous working day.")
        with st.expander("Add a campaign for this moment"):
            with st.form(_form_key(f"quick-campaign-{moment_id}-{year}")):
                name = st.text_input("Campaign name")
                brand = st.text_input("Brand")
                if st.form_submit_button("Add to My campaigns"):
                    try:
                        campaign = validate_campaign(
                            Campaign(name=name, brand=brand, moment_id=moment_id, year=year, category=category,
                                     region=region),
                            LIBRARY,
                        )
                        _persist(f"Added “{campaign.name}”.", lambda store: store.campaigns.append(campaign))
                        _form_done()
                    except PlanProblem as exc:
                        st.error(friendly_message(exc))


def page_welcome() -> None:
    st.markdown(
        """
        <section class="ps-hero">
          <div class="ps-eyebrow">NORWEGIAN MARKETING CALENDAR</div>
          <h1>Which moments matter—and <em>when do you have to start?</em></h1>
          <p>The commercial year in Norway, computed for any year from 2025 to 2035: helligdager, 17. mai, russetid,
          Black Week, morsdag and farsdag, fellesferie, back-to-school and the school breaks—each worked backwards
          into concept, creative, media and go-live deadlines.</p>
          <div class="ps-pills"><span class="ps-pill">computed holidays</span><span class="ps-pill">Easter-based dates</span>
          <span class="ps-pill">sourced date rules</span><span class="ps-pill">plan-back milestones</span>
          <span class="ps-pill">local campaigns</span><span class="ps-pill">.ics export</span>
          <span class="ps-pill">XLSX plan</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="ps-grid">
          <div class="ps-card"><b>01 · COMPUTE</b><h3>Every date from a rule</h3><p>Easter, the 2nd Sunday in
          February, ISO week 28, the Friday after the 4th Thursday of November. Nothing is typed in per year, so the
          calendar is right for 2025 and for 2035.</p></div>
          <div class="ps-card"><b>02 · CITE</b><h3>Sources, or an honest “convention”</h3><p>Holidays cite Lovdata;
          traditions cite SNL; school breaks that vary by kommune are shown as a range, not a guess. Black Week and
          julebord are labelled as conventions.</p></div>
          <div class="ps-card"><b>03 · PLAN BACK</b><h3>Deadlines you can import</h3><p>Lead times per category
          turn each moment into concept, creative, media-booking and go-live dates, then export to Google, Outlook or
          Apple Calendar.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### Try the demo in two minutes")
    st.markdown(
        f"1. The sidebar is set to **{_default_year()}**, **Food & drink** and **Hele landet**.\n"
        "2. Open **Planner**, click a bar (try *Black Week* or *17. mai*) and read its plan-back milestones.\n"
        "3. Open **Coming up** for the next 6–12 months: on track, late start or missed go-live.\n"
        "4. Open **My campaigns** to see the fictional brand *Fjellbrus* and its three campaigns.\n"
        "5. Open **Export** and download the `.ics` file for your calendar."
    )
    st.markdown(
        '<div class="boundary"><strong>Demo data:</strong> Fjellbrus is a fictional alcohol-free drinks brand '
        "invented for this example. It represents no real company, and its campaigns are illustrations.</div>",
        unsafe_allow_html=True,
    )


def page_planner() -> None:
    year, category, region, show_all = _selection()
    _header(
        "Step 1",
        f"The {year} marketing year",
        f"Moments for <strong>{LIBRARY.category_label(category)}</strong> in <strong>{LIBRARY.regions[region]}</strong>"
        " (public holidays always shown for context). Click a bar or diamond to see its plan-back milestones. "
        "⇢ marks a range that varies by kommune.",
    )
    planned = _planned(year, category, region, show_all)
    frame = moments_frame(LIBRARY, planned, TODAY)
    upcoming = frame[frame["Start"] > TODAY]
    cols = st.columns(4)
    cols[0].metric("Moments shown", len(frame))
    cols[1].metric("Public holidays", int(frame["Kind"].eq("Public holiday").sum()))
    cols[2].metric("Vary by kommune", int(frame["Varies locally"].eq("Yes — range").sum()))
    cols[3].metric("Next up", upcoming.iloc[0]["Moment"] if not upcoming.empty else "—")

    event = st.plotly_chart(
        timeline_figure(frame, year),
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key=f"timeline-{year}-{category}-{region}-{show_all}",
    )
    clicked = None
    points = getattr(getattr(event, "selection", None), "points", None) or []
    if points and points[0].get("customdata"):
        clicked = points[0]["customdata"][0]
    ids = list(dict.fromkeys(frame["id"]))  # a range crossing New Year can appear twice in one year
    names = dict(zip(frame["id"], frame["Moment"]))
    if not ids:
        st.info("No moments match this filter.")
        return
    first = upcoming.iloc[0]["id"] if not upcoming.empty else ids[0]
    linked = st.query_params.get("moment")
    default = clicked if clicked in ids else st.session_state.get("moment_pick", linked if linked in ids else first)
    chosen = st.selectbox(
        "Moment details", ids, index=ids.index(default) if default in ids else 0, format_func=names.get,
        key=f"moment-select-{clicked}",
    )
    st.session_state["moment_pick"] = chosen
    moment_details(chosen, year, category, region)

    with st.expander("All moments as a table"):
        view = frame.drop(columns=["id", "Notes", "Rule"]).copy()
        view["Status"] = view["Status"].map(STATUS_ICONS)
        st.dataframe(view, hide_index=True, use_container_width=True,
                     column_config={**DATE_COLUMNS, "Source": st.column_config.LinkColumn("Source")})


def page_coming_up() -> None:
    _, category, region, show_all = _selection()
    _header(
        "Step 2",
        "Coming up — and when to start",
        "The next months from today, across the year boundary. For each moment: the concept deadline for your "
        "category: on track, start soon, a late start (concept date passed, go-live still possible) or a missed "
        "go-live.",
    )
    months = st.slider("Horizon (months from today)", 6, 12, 12)
    start = max(TODAY, date(MIN_YEAR, 1, 1))
    occurrences = [occ for occ in LIBRARY.window(start, months, region) if occ.start >= TODAY]
    occurrences = select_occurrences(
        LIBRARY, occurrences, category, include_all=show_all, include_public_holidays=False
    )
    planned = plan_moments(LIBRARY, occurrences, _store().lead_times, category)
    frame = moments_frame(LIBRARY, planned, TODAY)
    if frame.empty:
        st.info("Nothing in this window for the chosen category.")
        return
    statuses = frame["Status"].value_counts()
    cols = st.columns(4)
    cols[0].metric("On track", int(statuses.get("on track", 0)), help="Concept deadline more than two weeks away")
    cols[1].metric("Start within 2 weeks", int(statuses.get("start soon", 0)))
    cols[2].metric("Late start", int(statuses.get("late start", 0)),
                   help="Concept deadline passed, but go-live is still ahead — plan a compressed timeline")
    cols[3].metric("Missed go-live", int(statuses.get("missed go-live", 0)),
                   help="The go-live date has passed; only a reactive presence is realistic")
    view = frame[["Moment", "Start", "End", "Varies locally", "Concept & brief", "Media booking", "Campaign live", "Status"]].copy()
    next_due = [next((m for m in item.milestones if m.due >= TODAY), None) for item in planned]
    view["Next deadline"] = [
        f"{m.label} · {m.due:%d.%m} ({(m.due - TODAY).days} d)" if m else "go-live date passed" for m in next_due
    ]
    view["Status"] = view["Status"].map(STATUS_ICONS)
    st.dataframe(view, hide_index=True, use_container_width=True, column_config=DATE_COLUMNS)
    st.caption(f"Lead times for {LIBRARY.category_label(category)}: " + ", ".join(
        f"{label.lower()} −{_store().lead_times[category][key]} wk" for key, label in MILESTONES
    ) + ". Change them under Lead times.")


def page_campaigns() -> None:
    year, category, region, _ = _selection()
    store = _store()
    _header(
        "Step 3",
        "My campaigns",
        "Link your own campaigns to a moment; SeasonSignal works out the deadlines. Campaigns are saved to a local "
        "JSON file on this computer.",
    )
    if not store.saved:
        st.info("You are looking at the fictional Fjellbrus demo. Your first change saves it to a local file; "
                "remove the demo campaigns whenever you like.")
    plans = _campaign_plans(warn=True)
    frame = campaigns_frame(LIBRARY, plans, TODAY)
    if frame.empty:
        st.info("No campaigns yet — add one below.")
    else:
        view = frame[["Campaign", "Brand", "Moment", "Moment start", "Next milestone", "Fictional"]].copy()
        view["Moment start"] = [f"{d:%d.%m.%Y}" for d in view["Moment start"]]
        st.dataframe(view, hide_index=True, use_container_width=True)
        for plan in plans:
            label = ("🧪 " if plan.campaign.fictional else "") + (
                f"{plan.campaign.name} · {plan.occurrence.moment.name_nb} {plan.campaign.year}"
            )
            with st.expander(label):
                st.markdown(f"**Moment:** {_span(plan.occurrence.start, plan.occurrence.end)}")
                if plan.campaign.notes:
                    st.caption(plan.campaign.notes)
                st.dataframe(_milestone_table(plan.milestones), hide_index=True, use_container_width=True)

    st.markdown("### Add a campaign")
    moment_ids = list(LIBRARY.moments)
    with st.form(_form_key("add-campaign")):
        c1, c2 = st.columns(2)
        name = c1.text_input("Campaign name")
        brand = c2.text_input("Brand")
        moment_id = c1.selectbox("Moment", moment_ids, format_func=lambda m: LIBRARY.moments[m].name_nb,
                                 index=moment_ids.index("syttende_mai"))
        camp_year = c2.selectbox("Year", list(range(MIN_YEAR, MAX_YEAR + 1)), index=year - MIN_YEAR)
        camp_category = c1.selectbox("Category (sets lead times)", CATEGORY_KEYS, index=CATEGORY_KEYS.index(category),
                                     format_func=LIBRARY.category_label)
        camp_region = c2.selectbox("Region", REGION_KEYS, index=REGION_KEYS.index(region), format_func=LIBRARY.regions.get)
        notes = st.text_area("Notes", height=80)
        if st.form_submit_button("Add campaign"):
            try:
                campaign = validate_campaign(
                    Campaign(name=name, brand=brand, moment_id=moment_id, year=int(camp_year),
                             category=camp_category, region=camp_region, notes=notes),
                    LIBRARY,
                )
            except PlanProblem as exc:
                st.error(friendly_message(exc))
            else:
                _persist(f"Added “{campaign.name}”.", lambda store: store.campaigns.append(campaign))
                _form_done()
                st.rerun()

    if store.campaigns:
        st.markdown("### Remove")
        c1, c2 = st.columns([2, 1])
        names = {c.id: f"{c.name} ({c.year})" for c in store.campaigns}
        to_remove = c1.selectbox("Campaign", list(names), format_func=names.get)
        if c1.button("Remove campaign"):
            def remove(saved):
                saved.campaigns = [c for c in saved.campaigns if c.id != to_remove]

            _persist("Campaign removed.", remove)
            st.rerun()
        if any(c.fictional for c in store.campaigns) and c2.button("Remove fictional demo campaigns"):
            def remove_demo(saved):
                saved.campaigns = [c for c in saved.campaigns if not c.fictional]

            _persist("Demo campaigns removed.", remove_demo)
            st.rerun()
    st.caption(f"File: {store.path}")


def page_lead_times() -> None:
    store = _store()
    _header(
        "Step 4",
        "Lead times",
        "Weeks before a moment starts. Defaults are planning conventions — grocery and travel partners plan earlier, "
        "so those categories start earlier. Edit them to match your organisation.",
    )
    frame = lead_times_frame(LIBRARY, store.lead_times)
    labels = [label for _key, label in MILESTONES]
    edited = st.data_editor(
        frame,
        hide_index=True,
        use_container_width=True,
        disabled=["Category", "key"],
        column_order=["Category", *labels],
        column_config={label: st.column_config.NumberColumn(label, min_value=0, max_value=52, step=1, format="%d wk")
                       for label in labels},
        key="lead-time-editor",
    )
    c1, c2 = st.columns([1, 1])
    if c1.button("Save lead times", type="primary"):
        table = {row["key"]: {key: row[label] for key, label in MILESTONES} for _, row in edited.iterrows()}
        clean = validate_lead_times(table)
        _persist("Lead times updated.", lambda saved: saved.lead_times.update(clean))
    if c2.button("Reset to defaults"):
        defaults = validate_lead_times(DEFAULT_LEAD_TIMES)
        _persist("Lead times reset.", lambda saved: setattr(saved, "lead_times", defaults))
        # The editor re-applies its stored edits on top of new data; drop them so it shows the defaults.
        st.session_state.pop("lead-time-editor", None)
        st.rerun()
    st.markdown(
        '<div class="boundary"><strong>Rules:</strong> whole weeks from 0 to 52, in order concept ≥ creative ≥ media '
        "booking ≥ live. Plan-back runs from the first day of a moment; for ranges that vary by kommune that is the "
        "earliest local start.</div>",
        unsafe_allow_html=True,
    )


def page_export() -> None:
    year, category, region, show_all = _selection()
    _header(
        "Step 5",
        "Export",
        "Download an .ics calendar (imports into Google, Outlook and Apple Calendar) or an XLSX plan. "
        "Exports follow the year, category and region chosen in the sidebar.",
    )
    planned = _planned(year, category, region, show_all)
    plans = _campaign_plans(year)
    c1, c2, c3 = st.columns(3)
    with_moments = c1.checkbox("Moments", value=True)
    with_milestones = c2.checkbox("Plan-back milestones", value=True)
    with_campaigns = c3.checkbox(f"My campaigns ({len(plans)} in {year})", value=True)
    items = []
    if with_moments or with_milestones:
        items = moment_items(planned, milestones=with_milestones, category=category)
        if not with_moments:
            items = [item for item in items if item.category != "Moment"]
    if with_campaigns:
        items += campaign_items(plans)
    name = f"SeasonSignal {year} — {LIBRARY.category_label(category)}"
    slug = f"seasonsignal-{year}-{category}-{region}"
    d1, d2 = st.columns(2)
    d1.download_button(f"Download .ics ({len(items)} events)", build_ics(items, name), f"{slug}.ics",
                       "text/calendar", type="primary", disabled=not items)
    sheets = {
        "Moments": moments_frame(LIBRARY, planned, TODAY),
        "Milestones": milestones_frame(planned, TODAY),
        "Campaigns": campaigns_frame(LIBRARY, plans, TODAY),
        "Lead times": lead_times_frame(LIBRARY, _store().lead_times),
        "About": about_frame(year, LIBRARY.regions[region], LIBRARY.category_label(category), TODAY),
    }
    d2.download_button("Download XLSX plan", build_xlsx(sheets), f"{slug}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("### Importing the .ics")
    st.markdown(
        "- **Google Calendar:** create a separate calendar first (*Settings → Add calendar → Create new calendar*), "
        "then *Settings → Import & export → Import* and pick that calendar. Deleting the calendar removes everything.\n"
        "- **Outlook:** *Add calendar → Upload from file*.\n"
        "- **Apple Calendar:** *File → Import*, then choose a new calendar.\n\n"
        "All events are all-day and marked *free*, so they never block meetings.\n\n"
        "**Updating later:** calendar apps differ in whether a re-import updates events they already have "
        "(Google Calendar usually keeps the old copy). The reliable way to refresh a plan is to delete the "
        "SeasonSignal calendar you created and import the new file into a fresh one."
    )


def page_sources() -> None:
    _header(
        "Reference",
        "Sources & method",
        "Every moment states its basis and its source. Where a date is set locally, the library says so and shows a "
        "range; where a moment is only a commercial convention, it says that too.",
    )
    year = st.session_state["year"]
    rows = []
    for moment in LIBRARY.moments.values():
        occ = LIBRARY.resolve(moment.id, year)
        rows.append({
            "Moment": moment.name_nb,
            "Basis": moment.basis,
            f"{year}": _span(occ.start, occ.end),
            "Varies": moment.varies,
            "Regional rules": ", ".join(LIBRARY.regions[v.region] for v in moment.variants),
            "Source": moment.source,
        })
    basis_counts = pd.Series([m.basis for m in LIBRARY.moments.values()]).value_counts()
    cols = st.columns(4)
    for col, basis in zip(cols, ("official", "tradition", "observed", "convention")):
        col.metric(basis.capitalize(), int(basis_counts.get(basis, 0)))
    frame = pd.DataFrame(rows)
    st.dataframe(frame, hide_index=True, use_container_width=True,
                 column_config={"Source": st.column_config.LinkColumn("Source")})
    st.markdown("### Basis")
    st.markdown(
        "- **official** — set by law or by the owning body (Lovdata for helligdager and høytidsdager).\n"
        "- **tradition** — a long-established Norwegian date rule documented by Store norske leksikon "
        "(morsdag = 2nd Sunday of February, farsdag = 2nd Sunday of November, advent, fastelavn, sankthans).\n"
        "- **observed** — set locally (school breaks). The national entry is a range; regional rules reproduce a "
        "kommune's published skolerute and say which school years were checked.\n"
        "- **convention** — commercial or cultural habits without an owner (Black Week, julebord, russetid). The "
        "note explains why and the source is the best available description."
    )
    st.markdown("### Method")
    st.markdown(
        "- Easter follows the Western (Gregorian) computus (`dateutil.easter`), matching helligdagsfredloven.\n"
        "- Week numbers are ISO 8601, as used in Norway.\n"
        "- Plan-back milestones are whole weeks before a moment's first day, moved back to the previous working "
        "day when they land on a weekend or public holiday.\n"
        "- The library was last reviewed on 1 October 2026. Russetid is changing (exam timing from 2026) and school "
        "routes change each year — re-check before you commit budget."
    )


PAGE_SLUGS = {
    "welcome": "Welcome",
    "planner": "1 · Planner",
    "coming-up": "2 · Coming up",
    "campaigns": "3 · My campaigns",
    "lead-times": "4 · Lead times",
    "export": "5 · Export",
    "sources": "Sources & method",
}

_ensure_state()

with st.sidebar:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f'<div class="ps-lockup">{mark}<div class="ps-name">Season<span>Signal</span></div></div>'
        '<p class="ps-tag">The Norwegian marketing year, worked backwards.</p>',
        unsafe_allow_html=True,
    )
    st.caption(f"Norwegian marketing calendar · v{__version__}")
    # Deep links such as ?page=planner&moment=black_week (bookmarks, screenshots).
    linked = PAGE_SLUGS.get(str(st.query_params.get("page", "")).lower(), "Welcome")
    page = st.radio("Workflow", list(PAGE_SLUGS.values()), index=list(PAGE_SLUGS.values()).index(linked))
    st.markdown("---")
    years = list(range(MIN_YEAR, MAX_YEAR + 1))
    st.selectbox("Year", years, index=years.index(_default_year()), key="year")
    st.selectbox("Your category", CATEGORY_KEYS, index=CATEGORY_KEYS.index("food"), key="category",
                 format_func=LIBRARY.category_label)
    st.selectbox("Region", REGION_KEYS, key="region", format_func=LIBRARY.regions.get)
    st.checkbox("Show moments outside my category", value=False, key="show_all")
    st.caption(f"{len(LIBRARY.moments)} moments · every date computed from a sourced rule")
    st.caption("Local mode · no telemetry · no accounts · campaigns stay in a file on this computer")

PAGES = {
    "Welcome": page_welcome,
    "1 · Planner": page_planner,
    "2 · Coming up": page_coming_up,
    "3 · My campaigns": page_campaigns,
    "4 · Lead times": page_lead_times,
    "5 · Export": page_export,
    "Sources & method": page_sources,
}
masthead()
try:
    PAGES[page]()
except Exception as exc:
    show_error(exc)
footer()
