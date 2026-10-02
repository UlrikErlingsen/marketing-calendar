"""Season Signal user interface: the Signal Hub entry point.

The only package under ``seasonsignal`` that imports Streamlit. ``render()`` draws the whole app on the current page
and never calls ``st.set_page_config``; the standalone ``app.py`` or Signal Hub owns the page config.
"""

from seasonsignal import __version__
from seasonsignal.ui import signal_theme
from seasonsignal.ui.app import render

APP_INFO = {"product": "Season Signal", "version": __version__, "repo": "marketing-calendar", "slug": "season"}

__all__ = ["APP_INFO", "render", "signal_theme"]
