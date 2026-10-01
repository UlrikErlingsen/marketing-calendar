"""Storage: the only module that reads or writes saved state.

Today this is one local JSON file holding campaigns and lead times. Everything else talks to ``load_store`` /
``update_store`` / ``save_store`` and the ``Store`` object, so a SQLite backend can replace this module without
touching callers.

Changes go through ``update_store``: it re-reads the file, applies the change and writes it back under a
process-wide lock, so two browser tabs (Streamlit sessions are threads in one process) never overwrite each
other's campaigns with a stale copy.

The file lives in ``data/seasonsignal.json`` next to the app (git-ignored), or in the folder named by the
``SEASONSIGNAL_DATA_DIR`` environment variable. Nothing is sent anywhere.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from .campaigns import Campaign, demo_campaigns
from .errors import PlanProblem
from .leadtimes import DEFAULT_LEAD_TIMES, validate_lead_times

STORE_VERSION = 1
_LOCK = threading.Lock()


def default_store_path() -> Path:
    base = os.getenv("SEASONSIGNAL_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "seasonsignal.json"


@dataclass
class Store:
    campaigns: list[Campaign]
    lead_times: dict[str, dict[str, int]]
    path: Path
    saved: bool = False

    def to_json(self) -> str:
        payload = {
            "version": STORE_VERSION,
            "lead_times": self.lead_times,
            "campaigns": [asdict(campaign) for campaign in self.campaigns],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def load_store(path: Path | None = None, *, demo_year: int | None = None) -> Store:
    """Load saved campaigns and lead times; with no file yet, start from defaults and the fictional demo."""
    path = Path(path) if path else default_store_path()
    if not path.exists():
        year = demo_year or date.today().year
        return Store(demo_campaigns(year), validate_lead_times(DEFAULT_LEAD_TIMES), path, saved=False)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanProblem(f"Could not read {path.name}: {exc}. Move the file aside to start fresh.") from exc
    if not isinstance(raw, dict) or raw.get("version") != STORE_VERSION:
        raise PlanProblem(f"{path.name} is not a SeasonSignal v{STORE_VERSION} file.")
    # Merge per milestone, so a file written before a category or milestone existed still loads.
    stored = raw.get("lead_times") or {}
    if not isinstance(stored, dict):
        raise PlanProblem(f"{path.name}: 'lead_times' must be a table of categories.")
    lead_times = {
        category: {**DEFAULT_LEAD_TIMES.get(category, {}), **(stored.get(category) or {})}
        for category in {*DEFAULT_LEAD_TIMES, *stored}
    }
    campaigns = [Campaign.from_dict(item) for item in raw.get("campaigns") or []]
    return Store(campaigns, validate_lead_times(lead_times), path, saved=True)


def save_store(store: Store) -> Path:
    """Write the store atomically (unique temp file + replace) so a crash never leaves half a file."""
    store.lead_times = validate_lead_times(store.lead_times)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    temp = store.path.with_name(f".{store.path.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(store.to_json(), encoding="utf-8")
    try:
        for attempt in range(5):
            try:
                os.replace(temp, store.path)
                break
            except PermissionError:
                # Windows: a sync client (OneDrive) or virus scanner may hold the file for a moment.
                if attempt == 4:
                    raise
                time.sleep(0.1 * (attempt + 1))
    finally:
        temp.unlink(missing_ok=True)
    store.saved = True
    return store.path


def update_store(change: Callable[[Store], None], path: Path | None = None, *, demo_year: int | None = None) -> Store:
    """Re-read the saved store, apply ``change`` to it and save — all under one lock. Returns the saved store.

    ``change`` may raise (e.g. PlanProblem from validation); nothing is written in that case.
    """
    with _LOCK:
        store = load_store(path, demo_year=demo_year)
        change(store)
        save_store(store)
        return store
