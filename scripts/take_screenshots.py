"""Capture README screenshots of a running SeasonSignal app into assets/.

Dev-only helper. Needs `pip install playwright` and an installed Microsoft Edge (or Chrome; set
SEASONSIGNAL_SHOT_CHANNEL=chrome). Start the app first with an empty data folder so the fictional demo shows:

    set SEASONSIGNAL_DATA_DIR=%TEMP%\\seasonsignal-shots
    python -m streamlit run app.py --server.port=8588
    python scripts/take_screenshots.py http://127.0.0.1:8588
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SHOTS = {
    "screenshot-welcome.png": "page=welcome",
    "screenshot-planner.png": "page=planner&moment=black_week",
    "screenshot-plan-back.png": "page=planner&moment=black_week",
    "screenshot-coming-up.png": "page=coming-up",
    "screenshot-campaigns.png": "page=campaigns",
    "screenshot-export.png": "page=export",
}


def main(base_url: str) -> None:
    channel = os.getenv("SEASONSIGNAL_SHOT_CHANNEL", "msedge")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=channel)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1, color_scheme="light")
        for filename, query in SHOTS.items():
            page.goto(f"{base_url}/?{query}")
            page.wait_for_selector(".ps-footer", timeout=60_000)
            if "planner" in query:
                page.wait_for_selector(".js-plotly-plot .trace", timeout=60_000)
            page.wait_for_timeout(1500)  # let fonts, charts and toasts settle
            if filename == "screenshot-plan-back.png":
                # Streamlit scrolls inside its own container, so scroll to the details card before capturing.
                page.locator("h3").first.scroll_into_view_if_needed()
                page.mouse.wheel(0, -120)
                page.wait_for_timeout(500)
            page.screenshot(path=str(ASSETS / filename))
            print(f"saved {filename}")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8588")
