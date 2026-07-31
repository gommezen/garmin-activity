# Shindō Phase 1 — The Spine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the daily loop — Home, Start session, Brief, Debrief — running on real Garmin data in the Dojo layout, with Kurosawa's voice streamed live.

**Architecture:** Deterministic Python engines (`prescriber`, `verdict`, `rank`) read DataFrames from a new `src/queries.py` and emit JSON. A FastAPI app in `app/api` serves that JSON and streams Claude-rendered dialogue over SSE. A Vite/React frontend in `app/web` renders the three-region Dojo shell. Claude never produces a number — it only voices JSON the engines already decided.

**Tech Stack:** Python 3.12 · FastAPI · `anthropic` (AsyncAnthropic, `claude-opus-5`) · SQLite · pandas · pytest · Vite + React + Tailwind · `uv` for Python deps · npm for JS

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-07-31-shindo-design.md`. Phase 1 covers beats 04, 05, 06, 07 only.
- **Python deps install with `uv`**, not pip: `VIRTUAL_ENV=$PWD/.venv uv pip install …`. The venv has no `pip` binary.
- **Run pytest as** `.venv/bin/python -m pytest` from the repo root.
- **Engines are pure.** Every engine function takes `today: date` as an explicit argument and never calls `date.today()` internally. Engines take DataFrames, never DB connections.
- **Claude never invents numbers.** All figures shown to the user come from engine JSON.
- **Model is `claude-opus-5`** with `output_config={"effort": "low"}`. No `temperature`, `top_p`, or `top_k` — they return 400 on this model. No assistant prefill.
- **Append-only:** `prescriptions` and `debriefs` are insert-only, except one-time fills of `debriefs.feel` and the follow-up pair, each guarded by a NULL check.
- **Design tokens** (use verbatim): `--ink:#0C0B0A` `--ink-2:#141210` `--washi:#F2EDE4` `--washi-2:#E8DFCD` `--washi-3:#D6CEC0` `--stone:#8E8779` `--stone-2:#6F6759` `--stone-3:#A79E90` `--gold:#C9A227` `--crimson:#B8382C` `--jade:#5B7C6E`.
- **Type:** Source Serif 4 (Kurosawa's voice, italic) · Inter (labels/UI) · JetBrains Mono (every number).
- **Layout law:** nav strip (46px) · sensei rail (~30%) · workspace. His word always sits on the art; numbers always sit on washi paper.
- **Never commit** `.env`, `data/`, or `.superpowers/`.
- **Phase 1 has no onboarding.** `get_profile()` returns inferred defaults. Phase 2 replaces them with stated goals.

---

## File Structure

**Backend**

| File | Responsibility |
|---|---|
| `src/db.py` (modify) | Add three schemas to `_connect()`. Nothing else changes. |
| `src/store.py` (new) | Read/write `profile`, `prescriptions`, `debriefs`. No business logic. |
| `src/queries.py` (new) | Windowed DataFrame helpers over `db.load_dataframe()` / `db.load_laps_dataframe()`. |
| `src/rank.py` (new) | Streak calculation. (Composite grade is Phase 3.) |
| `src/verdict.py` (new) | Judge a completed run → verdict dict. |
| `src/prescriber.py` (new) | Decide today's session → prescription dict. |
| `app/api/persona.py` (new) | System prompt, register instructions, `PROMPT_VERSION`. |
| `app/api/sensei.py` (new) | Claude streaming wrapper. The only file that imports `anthropic`. |
| `app/api/main.py` (new) | FastAPI app and routes. |

**Frontend**

| File | Responsibility |
|---|---|
| `app/web/package.json`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js`, `index.html` | Build config |
| `app/web/src/styles/tokens.css` | Design tokens + font faces |
| `app/web/src/lib/sse.js` | `streamSSE(url, opts, onEvent)` — fetch + ReadableStream parser |
| `app/web/src/components/Dojo.jsx` | Three-region shell |
| `app/web/src/components/RailMedia.jsx` | Video-or-poster with reduced-motion fallback |
| `app/web/src/components/Tile.jsx` | Washi stat tile |
| `app/web/src/screens/{Home,Session,Brief,Debrief}.jsx` | Beats 04–07 |
| `app/web/src/App.jsx`, `src/main.jsx` | Router + mount |
| `app/web/public/art/*` | Higgsfield posters and loops |

**Tests:** `tests/test_store.py`, `tests/test_queries.py`, `tests/test_rank.py`, `tests/test_verdict.py`, `tests/test_prescriber.py`, `tests/test_api.py`

---

## Task 1: Schema and store

**Files:**
- Modify: `src/db.py:44-50` (add schemas to `_connect()`)
- Create: `src/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `db.DB_PATH`, `db._connect()`
- Produces:
  - `store.get_profile() -> dict` — keys `display_name, goal_type, goal_target, goal_date, days_available (list[str]), level, weekly_volume_lo, weekly_volume_hi, units, max_hr`
  - `store.save_prescription(date_iso: str, prescription: dict, dialogue: str, word: str, model: str, prompt_version: str) -> int`
  - `store.get_prescription(date_iso: str) -> dict | None` — keys `id, date, prescription, dialogue, word`
  - `store.save_debrief(activity_id: int, prescription_id: int | None, verdict: dict, dialogue: str, instruction: str | None, model: str, prompt_version: str) -> int`
  - `store.get_debrief_by_activity(activity_id: int) -> dict | None`
  - `store.get_debrief(debrief_id: int) -> dict | None`
  - `store.recent_instructions(limit: int = 3) -> list[str]`
  - `store.first_prescription_date() -> str | None` — the date the streak may start from
  - `store.set_feel(debrief_id: int, feel: str) -> bool` — False if already set
  - `store.set_followup(debrief_id: int, question: str, answer: str) -> bool` — False if already set

- [ ] **Step 1: Write the failing test**

Create `tests/test_store.py`:

```python
"""Tests for src.store — append-only prescription and debrief storage."""

import pytest

from src import db, store


@pytest.fixture(autouse=True)
def _patch_db_path(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")


class TestProfile:
    def test_defaults_when_no_row(self):
        p = store.get_profile()
        assert p["units"] == "km"
        assert p["goal_type"] == "return_to_running"
        assert p["days_available"] == ["Mon", "Wed", "Fri", "Sat"]


class TestPrescriptions:
    def test_save_and_get(self):
        pid = store.save_prescription(
            "2026-08-03", {"session_type": "easy"}, "Run slow.", "Slow is fast.",
            "claude-opus-5", "v1",
        )
        assert pid > 0
        got = store.get_prescription("2026-08-03")
        assert got["prescription"]["session_type"] == "easy"
        assert got["dialogue"] == "Run slow."
        assert got["word"] == "Slow is fast."

    def test_missing_date_returns_none(self):
        assert store.get_prescription("2026-01-01") is None

    def test_first_prescription_date(self):
        assert store.first_prescription_date() is None
        store.save_prescription("2026-08-05", {}, "a", "w", "m", "v")
        store.save_prescription("2026-08-03", {}, "b", "w", "m", "v")
        assert store.first_prescription_date() == "2026-08-03"

    def test_one_per_date(self):
        store.save_prescription("2026-08-03", {}, "a", "w", "m", "v")
        with pytest.raises(Exception):
            store.save_prescription("2026-08-03", {}, "b", "w", "m", "v")


class TestDebriefs:
    def test_save_and_fetch_by_activity(self):
        did = store.save_debrief(
            1001, None, {"assessment": "solid"}, "You held the pace.",
            "Rest tomorrow.", "claude-opus-5", "v1",
        )
        got = store.get_debrief_by_activity(1001)
        assert got["id"] == did
        assert got["verdict"]["assessment"] == "solid"
        assert got["instruction"] == "Rest tomorrow."

    def test_recent_instructions_newest_first(self):
        store.save_debrief(1, None, {}, "d", "first", "m", "v")
        store.save_debrief(2, None, {}, "d", "second", "m", "v")
        store.save_debrief(3, None, {}, "d", "third", "m", "v")
        assert store.recent_instructions(2) == ["third", "second"]

    def test_null_instruction_skipped_in_memory(self):
        store.save_debrief(1, None, {}, "d", None, "m", "v")
        store.save_debrief(2, None, {}, "d", "kept", "m", "v")
        assert store.recent_instructions() == ["kept"]


class TestGuardedFills:
    def test_feel_set_once(self):
        did = store.save_debrief(1, None, {}, "d", None, "m", "v")
        assert store.set_feel(did, "good") is True
        assert store.set_feel(did, "flat") is False
        assert store.get_debrief(did)["feel"] == "good"

    def test_followup_set_once(self):
        did = store.save_debrief(1, None, {}, "d", None, "m", "v")
        assert store.set_followup(did, "Why?", "Because.") is True
        assert store.set_followup(did, "Again?", "No.") is False
        got = store.get_debrief(did)
        assert got["followup_q"] == "Why?"
        assert got["followup_a"] == "Because."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.store'`

- [ ] **Step 3: Add the three schemas to `src/db.py`**

Insert after `SCHEMA_LAPS` (line 41):

```python
SCHEMA_PROFILE = """
CREATE TABLE IF NOT EXISTS profile (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    display_name      TEXT,
    goal_type         TEXT,
    goal_target       TEXT,
    goal_date         TEXT,
    days_available    TEXT,
    level             TEXT,
    weekly_volume_lo  REAL,
    weekly_volume_hi  REAL,
    pb_json           TEXT,
    units             TEXT DEFAULT 'km',
    max_hr            REAL,
    created_at        TEXT,
    updated_at        TEXT
)
"""

SCHEMA_PRESCRIPTIONS = """
CREATE TABLE IF NOT EXISTS prescriptions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    date               TEXT NOT NULL UNIQUE,
    prescription_json  TEXT NOT NULL,
    brief_dialogue     TEXT,
    word               TEXT,
    model              TEXT NOT NULL,
    prompt_version     TEXT NOT NULL,
    created_at         TEXT NOT NULL
)
"""

SCHEMA_DEBRIEFS = """
CREATE TABLE IF NOT EXISTS debriefs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER,
    prescription_id INTEGER,
    verdict_json    TEXT NOT NULL,
    dialogue        TEXT NOT NULL,
    instruction     TEXT,
    feel            TEXT,
    followup_q      TEXT,
    followup_a      TEXT,
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
)
"""
```

Then extend `_connect()` (line 44) so it creates them:

```python
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA_ACTIVITIES)
    conn.execute(SCHEMA_LAPS)
    conn.execute(SCHEMA_PROFILE)
    conn.execute(SCHEMA_PRESCRIPTIONS)
    conn.execute(SCHEMA_DEBRIEFS)
    conn.commit()
    return conn
```

- [ ] **Step 4: Write `src/store.py`**

```python
"""Append-only storage for profile, prescriptions, and debriefs."""

import json
import sqlite3
from datetime import datetime, timezone

from src.db import _connect

DEFAULT_PROFILE = {
    "display_name": None,
    "goal_type": "return_to_running",
    "goal_target": None,
    "goal_date": None,
    "days_available": ["Mon", "Wed", "Fri", "Sat"],
    "level": "returning",
    "weekly_volume_lo": None,
    "weekly_volume_hi": None,
    "units": "km",
    "max_hr": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_profile() -> dict:
    """Return the single profile row, falling back to inferred defaults.

    Phase 1 has no onboarding, so the defaults are what the prescriber runs on.
    max_hr falls back to the highest HR observed across stored activities.
    """
    conn = _connect()
    row = conn.execute(
        """SELECT display_name, goal_type, goal_target, goal_date, days_available,
                  level, weekly_volume_lo, weekly_volume_hi, units, max_hr
           FROM profile WHERE id = 1"""
    ).fetchone()
    observed = conn.execute("SELECT MAX(max_hr) FROM activities").fetchone()[0]
    conn.close()

    profile = dict(DEFAULT_PROFILE)
    if row:
        keys = list(DEFAULT_PROFILE)
        for key, value in zip(keys, row):
            if value is not None:
                profile[key] = value
        if isinstance(profile["days_available"], str):
            profile["days_available"] = json.loads(profile["days_available"])
    if profile["max_hr"] is None:
        profile["max_hr"] = observed
    return profile


def save_prescription(date_iso, prescription, dialogue, word, model, prompt_version) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO prescriptions
               (date, prescription_json, brief_dialogue, word, model,
                prompt_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (date_iso, json.dumps(prescription), dialogue, word, model,
             prompt_version, _now()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"prescription already exists for {date_iso}")
    finally:
        conn.close()


def get_prescription(date_iso: str) -> dict | None:
    conn = _connect()
    row = conn.execute(
        """SELECT id, date, prescription_json, brief_dialogue, word
           FROM prescriptions WHERE date = ?""",
        (date_iso,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "date": row[1], "prescription": json.loads(row[2]),
            "dialogue": row[3], "word": row[4]}


def first_prescription_date() -> str | None:
    """Earliest prescription date — the streak cannot start before this."""
    conn = _connect()
    row = conn.execute("SELECT MIN(date) FROM prescriptions").fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def save_debrief(activity_id, prescription_id, verdict, dialogue, instruction,
                 model, prompt_version) -> int:
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO debriefs
           (activity_id, prescription_id, verdict_json, dialogue, instruction,
            model, prompt_version, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (activity_id, prescription_id, json.dumps(verdict), dialogue,
         instruction, model, prompt_version, _now()),
    )
    conn.commit()
    debrief_id = cur.lastrowid
    conn.close()
    return debrief_id


_DEBRIEF_COLS = """id, activity_id, prescription_id, verdict_json, dialogue,
                   instruction, feel, followup_q, followup_a"""


def _row_to_debrief(row) -> dict:
    return {"id": row[0], "activity_id": row[1], "prescription_id": row[2],
            "verdict": json.loads(row[3]), "dialogue": row[4],
            "instruction": row[5], "feel": row[6],
            "followup_q": row[7], "followup_a": row[8]}


def get_debrief(debrief_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute(
        f"SELECT {_DEBRIEF_COLS} FROM debriefs WHERE id = ?", (debrief_id,)
    ).fetchone()
    conn.close()
    return _row_to_debrief(row) if row else None


def get_debrief_by_activity(activity_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute(
        f"SELECT {_DEBRIEF_COLS} FROM debriefs WHERE activity_id = ?", (activity_id,)
    ).fetchone()
    conn.close()
    return _row_to_debrief(row) if row else None


def recent_instructions(limit: int = 3) -> list[str]:
    """Kurosawa's memory: his last few instructions, newest first."""
    conn = _connect()
    rows = conn.execute(
        """SELECT instruction FROM debriefs
           WHERE instruction IS NOT NULL
           ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_feel(debrief_id: int, feel: str) -> bool:
    """One-time fill. Returns False if already set."""
    conn = _connect()
    cur = conn.execute(
        "UPDATE debriefs SET feel = ? WHERE id = ? AND feel IS NULL",
        (feel, debrief_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def set_followup(debrief_id: int, question: str, answer: str) -> bool:
    """One-time fill. Returns False if already set."""
    conn = _connect()
    cur = conn.execute(
        """UPDATE debriefs SET followup_q = ?, followup_a = ?
           WHERE id = ? AND followup_q IS NULL""",
        (question, answer, debrief_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`
Expected: PASS (11 tests)

- [ ] **Step 6: Run the whole suite to confirm no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: all pre-existing tests still pass

- [ ] **Step 7: Commit**

```bash
git add src/db.py src/store.py tests/test_store.py
git commit -m "feat(shindo): add profile/prescription/debrief schema and store"
```

---

## Task 2: Windowed queries

**Files:**
- Create: `src/queries.py`
- Test: `tests/test_queries.py`

**Interfaces:**
- Consumes: `db.load_dataframe()`, `db.load_laps_dataframe()`
- Produces:
  - `queries.runs_in_window(df, today: date, days: int) -> DataFrame`
  - `queries.km_in_window(df, today: date, days: int) -> float`
  - `queries.acwr(df, today: date) -> float | None` — None when fewer than 14 days of history
  - `queries.mean_run_distance(df, today: date, days: int = 28) -> float | None`
  - `queries.median_easy_pace_s(df, today: date, days: int = 28) -> float | None` — seconds per km
  - `queries.median_easy_hr(df, today: date, days: int = 28) -> float | None`
  - `queries.longest_run_km(df, today: date, days: int | None = None) -> float | None`
  - `queries.consecutive_run_days(df, today: date) -> int`
  - `queries.days_since_last_run(df, today: date) -> int | None`
  - `queries.weeks_with_min_runs(df, today: date, weeks: int = 3, min_runs: int = 2) -> bool`
  - `queries.laps_for(laps_df, activity_id: int) -> list[dict]` — each `{km, pace_s, hr, cadence, elev}`

An "easy" run for pace/HR medians = pace slower than the 40th percentile of the window (i.e. the slower 60% of runs), which excludes tempo and interval efforts without needing a session-type column.

- [ ] **Step 1: Write the failing test**

Create `tests/test_queries.py`:

```python
"""Tests for src.queries — windowed views used by the engines."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src import queries


def _df(rows):
    """rows: list of (days_ago, km, minutes, hr)."""
    today = datetime(2026, 8, 3, 8, 0, 0)
    data = []
    for i, (days_ago, km, minutes, hr) in enumerate(rows):
        data.append({
            "activity_id": 1000 + i,
            "name": "Run",
            "start_time": today - timedelta(days=days_ago),
            "distance_km": km,
            "duration_min": minutes,
            "pace_min_km": minutes / km,
            "avg_hr": hr,
        })
    return pd.DataFrame(data)


TODAY = date(2026, 8, 3)


class TestWindows:
    def test_runs_in_window_excludes_older(self):
        df = _df([(1, 5, 30, 145), (10, 5, 30, 145)])
        assert len(queries.runs_in_window(df, TODAY, 7)) == 1

    def test_km_in_window_sums(self):
        df = _df([(1, 5, 30, 145), (3, 7, 42, 145)])
        assert queries.km_in_window(df, TODAY, 7) == pytest.approx(12.0)

    def test_empty_window_is_zero(self):
        assert queries.km_in_window(_df([]), TODAY, 7) == 0.0


class TestAcwr:
    def test_none_when_history_too_short(self):
        df = _df([(1, 5, 30, 145), (3, 5, 30, 145)])
        assert queries.acwr(df, TODAY) is None

    def test_flat_load_is_about_one(self):
        rows = [(d, 5, 30, 145) for d in range(1, 29, 2)]
        assert queries.acwr(_df(rows), TODAY) == pytest.approx(1.0, abs=0.35)

    def test_spike_exceeds_one_four(self):
        rows = [(d, 3, 18, 145) for d in range(8, 29, 2)]
        rows += [(1, 15, 90, 150), (3, 15, 90, 150)]
        assert queries.acwr(_df(rows), TODAY) > 1.4


class TestPaceAndHr:
    def test_median_easy_pace_ignores_fast_efforts(self):
        rows = [(2, 6, 36, 140), (4, 6, 36, 140), (6, 6, 36, 140), (8, 5, 20, 178)]
        pace = queries.median_easy_pace_s(_df(rows), TODAY)
        assert pace == pytest.approx(360, abs=5)

    def test_none_without_data(self):
        assert queries.median_easy_pace_s(_df([]), TODAY) is None

    def test_median_easy_hr(self):
        rows = [(2, 6, 36, 140), (4, 6, 36, 144), (6, 6, 36, 142)]
        assert queries.median_easy_hr(_df(rows), TODAY) == pytest.approx(142, abs=2)


class TestStreaksAndGaps:
    def test_consecutive_run_days(self):
        df = _df([(1, 5, 30, 145), (2, 5, 30, 145), (3, 5, 30, 145), (9, 5, 30, 145)])
        assert queries.consecutive_run_days(df, TODAY) == 3

    def test_consecutive_zero_when_gap_yesterday(self):
        df = _df([(4, 5, 30, 145)])
        assert queries.consecutive_run_days(df, TODAY) == 0

    def test_days_since_last_run(self):
        assert queries.days_since_last_run(_df([(4, 5, 30, 145)]), TODAY) == 4

    def test_days_since_none_when_empty(self):
        assert queries.days_since_last_run(_df([]), TODAY) is None


class TestBase:
    def test_base_established(self):
        rows = []
        for week in range(3):
            rows += [(week * 7 + 1, 5, 30, 145), (week * 7 + 4, 5, 30, 145)]
        assert queries.weeks_with_min_runs(_df(rows), TODAY) is True

    def test_base_not_established_with_one_run_per_week(self):
        rows = [(1, 5, 30, 145), (8, 5, 30, 145), (15, 5, 30, 145)]
        assert queries.weeks_with_min_runs(_df(rows), TODAY) is False


class TestLaps:
    def test_laps_for_shapes_rows(self):
        laps = pd.DataFrame([
            {"activity_id": 1, "lap_index": 0, "distance_km": 1.0,
             "duration_min": 5.5, "pace_min_km": 5.5, "avg_hr": 150.0,
             "cadence": 172.0, "elevation_gain": 4.0},
        ])
        out = queries.laps_for(laps, 1)
        assert out == [{"km": 1.0, "pace_s": 330, "hr": 150, "cadence": 172, "elev": 4}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_queries.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.queries'`

- [ ] **Step 3: Write `src/queries.py`**

```python
"""Windowed views over activity data, shared by the prescriber and the judge.

Every function takes an explicit `today` so the engines stay testable.
"""

from datetime import date, timedelta

import pandas as pd

MIN_HISTORY_DAYS = 14


def _dates(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["start_time"]).dt.date


def runs_in_window(df: pd.DataFrame, today: date, days: int) -> pd.DataFrame:
    """Runs within the last `days` days, inclusive of today."""
    if df.empty:
        return df
    cutoff = today - timedelta(days=days)
    return df[(_dates(df) > cutoff) & (_dates(df) <= today)]


def km_in_window(df: pd.DataFrame, today: date, days: int) -> float:
    window = runs_in_window(df, today, days)
    return float(window["distance_km"].sum()) if not window.empty else 0.0


def history_days(df: pd.DataFrame, today: date) -> int:
    if df.empty:
        return 0
    return (today - min(_dates(df))).days


def acwr(df: pd.DataFrame, today: date) -> float | None:
    """Acute:chronic workload ratio. None when history is too short to mean anything."""
    if history_days(df, today) < MIN_HISTORY_DAYS:
        return None
    chronic_weekly = km_in_window(df, today, 28) / 4.0
    if chronic_weekly == 0:
        return None
    return km_in_window(df, today, 7) / chronic_weekly


def mean_run_distance(df: pd.DataFrame, today: date, days: int = 28) -> float | None:
    window = runs_in_window(df, today, days)
    if window.empty:
        return None
    return float(window["distance_km"].mean())


def _easy_runs(df: pd.DataFrame, today: date, days: int) -> pd.DataFrame:
    """The slower 60% of the window — excludes tempo and interval efforts."""
    window = runs_in_window(df, today, days).dropna(subset=["pace_min_km"])
    if window.empty:
        return window
    threshold = window["pace_min_km"].quantile(0.40)
    return window[window["pace_min_km"] >= threshold]


def median_easy_pace_s(df: pd.DataFrame, today: date, days: int = 28) -> float | None:
    easy = _easy_runs(df, today, days)
    if easy.empty:
        return None
    return float(easy["pace_min_km"].median() * 60)


def median_easy_hr(df: pd.DataFrame, today: date, days: int = 28) -> float | None:
    easy = _easy_runs(df, today, days).dropna(subset=["avg_hr"])
    if easy.empty:
        return None
    return float(easy["avg_hr"].median())


def longest_run_km(df: pd.DataFrame, today: date, days: int | None = None) -> float | None:
    window = df if days is None else runs_in_window(df, today, days)
    if window.empty:
        return None
    return float(window["distance_km"].max())


def consecutive_run_days(df: pd.DataFrame, today: date) -> int:
    """Run-days ending yesterday. Today is not counted — it hasn't happened yet."""
    if df.empty:
        return 0
    run_days = set(_dates(df))
    count, cursor = 0, today - timedelta(days=1)
    while cursor in run_days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def days_since_last_run(df: pd.DataFrame, today: date) -> int | None:
    if df.empty:
        return None
    return (today - max(_dates(df))).days


def weeks_with_min_runs(df: pd.DataFrame, today: date, weeks: int = 3,
                        min_runs: int = 2) -> bool:
    """True when every one of the last `weeks` 7-day blocks had >= min_runs runs."""
    if df.empty:
        return False
    for w in range(weeks):
        end = today - timedelta(days=7 * w)
        start = end - timedelta(days=7)
        block = df[(_dates(df) > start) & (_dates(df) <= end)]
        if len(block) < min_runs:
            return False
    return True


def laps_for(laps_df: pd.DataFrame, activity_id: int) -> list[dict]:
    """Per-lap rows for one activity, shaped for the verdict JSON."""
    if laps_df.empty:
        return []
    rows = laps_df[laps_df["activity_id"] == activity_id].sort_values("lap_index")
    out = []
    for _, lap in rows.iterrows():
        out.append({
            "km": round(float(lap["distance_km"]), 2),
            "pace_s": int(round(float(lap["pace_min_km"]) * 60)),
            "hr": int(lap["avg_hr"]) if pd.notna(lap["avg_hr"]) else None,
            "cadence": int(lap["cadence"]) if pd.notna(lap["cadence"]) else None,
            "elev": int(lap["elevation_gain"]) if pd.notna(lap["elevation_gain"]) else None,
        })
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_queries.py -v`
Expected: PASS (16 tests)

- [ ] **Step 5: Commit**

```bash
git add src/queries.py tests/test_queries.py
git commit -m "feat(shindo): add windowed query helpers for the engines"
```

---

## Task 3: Streak

**Files:**
- Create: `src/rank.py`
- Test: `tests/test_rank.py`

**Interfaces:**
- Consumes: `queries` (dates only)
- Produces: `rank.streak(run_dates: set[date], rest_dates: set[date], today: date, since: date | None) -> int`

Composite grade (sessions × speed × distance) is Phase 3 and is deliberately not built here. Home only needs the streak.

- [ ] **Step 1: Write the failing test**

Create `tests/test_rank.py`:

```python
"""Tests for src.rank — the training streak."""

from datetime import date

from src import rank

TODAY = date(2026, 8, 3)


def d(day: int) -> date:
    return date(2026, 8, day)


class TestStreak:
    def test_consecutive_runs(self):
        runs = {d(1), d(2), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 3

    def test_prescribed_rest_does_not_break_it(self):
        runs = {d(1), d(3)}
        rest = {d(2)}
        assert rank.streak(runs, rest, TODAY, since=d(1)) == 3

    def test_unscheduled_skip_breaks_it(self):
        runs = {d(1), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 1

    def test_today_counts_when_already_run(self):
        runs = {d(2), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 2

    def test_today_not_yet_run_does_not_break_it(self):
        """Today is still in progress — the streak is measured to yesterday."""
        runs = {d(1), d(2)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 2

    def test_stops_at_since_date(self):
        """Runs before the first prescription are history, not streak."""
        runs = {d(1), d(2), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(2)) == 2

    def test_zero_before_any_prescription(self):
        assert rank.streak({d(1), d(2)}, set(), TODAY, since=None) == 0

    def test_zero_when_nothing_recent(self):
        assert rank.streak({date(2026, 7, 1)}, set(), TODAY, since=d(1)) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_rank.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.rank'`

- [ ] **Step 3: Write `src/rank.py`**

```python
"""Training streak.

A streak is consecutive days that were either a run or a *prescribed* rest day.
It counts only from `since` — the date of the first prescription — because runs
that predate the app were never prescribed and are history, not streak.
"""

from datetime import date, timedelta


def streak(run_dates: set[date], rest_dates: set[date], today: date,
           since: date | None) -> int:
    """Count back from today (or yesterday, if today hasn't happened yet)."""
    if since is None:
        return 0

    counted = run_dates | rest_dates
    cursor = today if today in counted else today - timedelta(days=1)

    count = 0
    while cursor >= since and cursor in counted:
        count += 1
        cursor -= timedelta(days=1)
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_rank.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/rank.py tests/test_rank.py
git commit -m "feat(shindo): add training streak calculation"
```

---

## Task 4: The judge

**Files:**
- Create: `src/verdict.py`
- Test: `tests/test_verdict.py`

**Interfaces:**
- Consumes: `queries.*`
- Produces: `verdict.judge(run: dict, df, laps_df, today: date, prescription: dict | None, last_instructions: list[str]) -> dict`

`run` is a dict with keys `activity_id, start_time (datetime), distance_km, duration_min, pace_min_km, avg_hr`.

Verdict shape:

```python
{
  "state": "new_run",
  "run": {"activity_id": int, "date": "YYYY-MM-DD", "km": float,
          "pace_s": int, "avg_hr": int | None, "duration_s": int,
          "laps": [ ... ]},
  "vs_self": {"pace_vs_4wk_pct": float | None,
              "dist_vs_avg_km": float | None,
              "hr_at_pace": "low" | "normal" | "elevated" | None},
  "vs_prescription": {...} | None,
  "flags": [str, ...],
  "assessment": "caution" | "excellent" | "easy" | "solid",
  "streak": {"runs_7d": int, "km_7d": float, "acwr": float | None,
             "days_since_last": int | None},
  "last_instructions": [str, ...],
}
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_verdict.py`:

```python
"""Tests for src.verdict — the deterministic judge."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src import verdict

TODAY = date(2026, 8, 3)
BASE = datetime(2026, 8, 3, 8, 0, 0)


def _history(rows):
    """rows: list of (days_ago, km, minutes, hr)."""
    return pd.DataFrame([
        {"activity_id": 1000 + i, "name": "Run",
         "start_time": BASE - timedelta(days=days_ago),
         "distance_km": km, "duration_min": minutes,
         "pace_min_km": minutes / km, "avg_hr": hr}
        for i, (days_ago, km, minutes, hr) in enumerate(rows)
    ])


def _run(km=6.0, minutes=37.0, hr=151.0, days_ago=0):
    return {"activity_id": 9001, "start_time": BASE - timedelta(days=days_ago),
            "distance_km": km, "duration_min": minutes,
            "pace_min_km": minutes / km, "avg_hr": hr}


STEADY = [(d, 6.0, 37.0, 150.0) for d in range(2, 29, 3)]
NO_LAPS = pd.DataFrame()


class TestShape:
    def test_core_fields_present(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["state"] == "new_run"
        assert v["run"]["km"] == 6.0
        assert v["run"]["pace_s"] == 370
        assert set(v) >= {"run", "vs_self", "flags", "assessment", "streak"}

    def test_memory_passed_through(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None,
                          ["Rest tomorrow."])
        assert v["last_instructions"] == ["Rest tomorrow."]


class TestAssessment:
    def test_solid_is_the_default(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "solid"

    def test_caution_on_load_spike(self):
        rows = [(d, 3.0, 18.0, 145.0) for d in range(8, 29, 2)]
        rows += [(1, 15.0, 90.0, 150.0), (3, 15.0, 90.0, 150.0)]
        v = verdict.judge(_run(), _history(rows), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "caution"
        assert "load_spike" in v["flags"]

    def test_caution_on_oversized_run(self):
        run = _run(km=12.0, minutes=74.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "caution"

    def test_excellent_when_faster_at_normal_hr(self):
        run = _run(km=6.0, minutes=34.0, hr=150.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "excellent"

    def test_easy_when_slower_at_low_hr(self):
        run = _run(km=6.0, minutes=41.0, hr=132.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "easy"


class TestFlags:
    def test_negative_split(self):
        laps = pd.DataFrame([
            {"activity_id": 9001, "lap_index": 0, "distance_km": 1.0,
             "duration_min": 6.4, "pace_min_km": 6.4, "avg_hr": 148.0,
             "cadence": 170.0, "elevation_gain": 2.0},
            {"activity_id": 9001, "lap_index": 1, "distance_km": 1.0,
             "duration_min": 6.0, "pace_min_km": 6.0, "avg_hr": 152.0,
             "cadence": 172.0, "elevation_gain": 2.0},
        ])
        v = verdict.judge(_run(), _history(STEADY), laps, TODAY, None, [])
        assert "negative_split" in v["flags"]
        assert len(v["run"]["laps"]) == 2

    def test_long_gap(self):
        v = verdict.judge(_run(), _history([(20, 6.0, 37.0, 150.0)]),
                          NO_LAPS, TODAY, None, [])
        assert "long_gap" in v["flags"]

    def test_longest_run_4wk(self):
        run = _run(km=9.0, minutes=56.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert "longest_run_4wk" in v["flags"]


class TestVsPrescription:
    def test_none_without_prescription(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["vs_prescription"] is None

    def test_in_band(self):
        p = {"distance_km": 6.0, "pace_band_s": [360, 380]}
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, p, [])
        assert v["vs_prescription"]["pace"] == "in_band"

    def test_above_band(self):
        p = {"distance_km": 6.0, "pace_band_s": [380, 400]}
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, p, [])
        assert v["vs_prescription"]["pace"] == "above_band"
        assert v["vs_prescription"]["distance_delta_km"] == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.verdict'`

- [ ] **Step 3: Write `src/verdict.py`**

```python
"""The judge: turn a completed run into a verdict, deterministically.

Nothing here talks to Claude. Every number the sensei later says out loud
originates in this dict.
"""

from datetime import date

import pandas as pd

from src import queries

CAUTION_ACWR = 1.4
CAUTION_DISTANCE_RATIO = 1.6
EXCELLENT_PACE_PCT = 3.0
EASY_PACE_PCT = -5.0
HR_ELEVATED_DELTA = 8.0
HR_LOW_DELTA = -8.0
LONG_GAP_DAYS = 7


def _hr_at_pace(run_hr, baseline_hr) -> str | None:
    if run_hr is None or baseline_hr is None:
        return None
    delta = run_hr - baseline_hr
    if delta >= HR_ELEVATED_DELTA:
        return "elevated"
    if delta <= HR_LOW_DELTA:
        return "low"
    return "normal"


def judge(run: dict, df: pd.DataFrame, laps_df: pd.DataFrame, today: date,
          prescription: dict | None, last_instructions: list[str]) -> dict:
    """Judge one completed run against the runner's own history."""
    run_date = run["start_time"].date()
    pace_s = int(round(run["pace_min_km"] * 60))

    # Exclude the run being judged from its own baselines.
    history = df[df["activity_id"] != run["activity_id"]] if not df.empty else df

    baseline_pace_s = queries.median_easy_pace_s(history, today)
    baseline_hr = queries.median_easy_hr(history, today)
    mean_dist = queries.mean_run_distance(history, today)
    ratio = queries.acwr(history, today)
    laps = queries.laps_for(laps_df, run["activity_id"])

    pace_vs_4wk_pct = None
    if baseline_pace_s:
        pace_vs_4wk_pct = round((baseline_pace_s - pace_s) / baseline_pace_s * 100, 1)

    hr_at_pace = _hr_at_pace(run.get("avg_hr"), baseline_hr)

    flags: list[str] = []
    if ratio is not None and ratio > CAUTION_ACWR:
        flags.append("load_spike")
    if len(laps) >= 2:
        first, second = laps[0]["pace_s"], laps[-1]["pace_s"]
        if second < first:
            flags.append("negative_split")
    gap = queries.days_since_last_run(history, run_date)
    if gap is not None and gap > LONG_GAP_DAYS:
        flags.append("long_gap")
    longest_4wk = queries.longest_run_km(history, today, days=28)
    if longest_4wk is None or run["distance_km"] > longest_4wk:
        flags.append("longest_run_4wk")

    # Assessment — ordered, first match wins.
    oversized = mean_dist is not None and run["distance_km"] > mean_dist * CAUTION_DISTANCE_RATIO
    if (ratio is not None and ratio > CAUTION_ACWR) or hr_at_pace == "elevated" or oversized:
        assessment = "caution"
    elif pace_vs_4wk_pct is not None and pace_vs_4wk_pct >= EXCELLENT_PACE_PCT \
            and hr_at_pace in (None, "normal", "low"):
        assessment = "excellent"
    elif pace_vs_4wk_pct is not None and pace_vs_4wk_pct <= EASY_PACE_PCT \
            and hr_at_pace in (None, "normal", "low"):
        assessment = "easy"
    else:
        assessment = "solid"

    vs_prescription = None
    if prescription:
        # "Above band" means above the prescribed *effort* — i.e. ran faster than
        # told, which is fewer seconds per km. This matches the storyboard's
        # "3 of 3 runs above band", where the sensei is telling you to hold back.
        lo, hi = prescription.get("pace_band_s", [None, None])
        if lo is None:
            band = None
        elif pace_s < lo:
            band = "above_band"
        elif pace_s > hi:
            band = "below_band"
        else:
            band = "in_band"
        vs_prescription = {
            "pace": band,
            "distance_delta_km": round(
                run["distance_km"] - prescription.get("distance_km", 0), 2),
        }

    return {
        "state": "new_run",
        "run": {
            "activity_id": run["activity_id"],
            "date": run_date.isoformat(),
            "km": round(float(run["distance_km"]), 2),
            "pace_s": pace_s,
            "avg_hr": int(run["avg_hr"]) if run.get("avg_hr") else None,
            "duration_s": int(round(run["duration_min"] * 60)),
            "laps": laps,
        },
        "vs_self": {
            "pace_vs_4wk_pct": pace_vs_4wk_pct,
            "dist_vs_avg_km": round(run["distance_km"] - mean_dist, 2) if mean_dist else None,
            "hr_at_pace": hr_at_pace,
        },
        "vs_prescription": vs_prescription,
        "flags": flags,
        "assessment": assessment,
        "streak": {
            "runs_7d": len(queries.runs_in_window(df, today, 7)),
            "km_7d": round(queries.km_in_window(df, today, 7), 1),
            "acwr": round(ratio, 2) if ratio is not None else None,
            "days_since_last": gap,
        },
        "last_instructions": last_instructions,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_verdict.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add src/verdict.py tests/test_verdict.py
git commit -m "feat(shindo): add deterministic verdict engine"
```

---

## Task 5: The prescriber

**Files:**
- Create: `src/prescriber.py`
- Test: `tests/test_prescriber.py`

**Interfaces:**
- Consumes: `queries.*`, `store.get_profile()` shape
- Produces: `prescriber.prescribe(profile: dict, df, today: date, last_feel: str | None) -> dict`

Prescription shape (matches the spec):

```python
{
  "date": "YYYY-MM-DD", "week_n": int,
  "session_type": "easy" | "long" | "tempo" | "rest",
  "distance_km": float | None,       # None on a rest day
  "pace_band_s": [int, int] | None,
  "hr_cap": int | None,
  "week": {"km_so_far": float, "target_km": float},
  "evidence": [{"label": str, "value": str}, ...],
}
```

`word` is generated by Claude in Task 7, not here.

Rules, first match wins: `rest` → `long` → `tempo` → `easy`. Time-based goals are `break_45` and any `other` carrying a target time; `first_10k` and `return_to_running` never get tempo.

- [ ] **Step 1: Write the failing test**

Create `tests/test_prescriber.py`:

```python
"""Tests for src.prescriber — the rule engine behind the brief."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src import prescriber

BASE = datetime(2026, 8, 3, 8, 0, 0)   # a Monday
MONDAY = date(2026, 8, 3)
SATURDAY = date(2026, 8, 8)


def _history(rows):
    return pd.DataFrame([
        {"activity_id": 1000 + i, "name": "Run",
         "start_time": BASE - timedelta(days=days_ago),
         "distance_km": km, "duration_min": minutes,
         "pace_min_km": minutes / km, "avg_hr": hr}
        for i, (days_ago, km, minutes, hr) in enumerate(rows)
    ])


def _profile(**over):
    p = {"goal_type": "return_to_running", "goal_target": None,
         "days_available": ["Mon", "Wed", "Fri", "Sat"], "max_hr": 190.0}
    p.update(over)
    return p


# Two runs a week for four weeks — base established, steady load.
STEADY = []
for _w in range(4):
    STEADY += [(_w * 7 + 2, 6.0, 37.0, 148.0), (_w * 7 + 5, 6.0, 37.0, 148.0)]


class TestRestRule:
    def test_rest_when_day_not_available(self):
        p = prescriber.prescribe(_profile(days_available=["Tue"]),
                                 _history(STEADY), MONDAY, None)
        assert p["session_type"] == "rest"
        assert p["distance_km"] is None

    def test_rest_on_load_spike(self):
        rows = [(d, 3.0, 18.0, 145.0) for d in range(8, 29, 2)]
        rows += [(1, 15.0, 90.0, 150.0), (2, 15.0, 90.0, 150.0)]
        p = prescriber.prescribe(_profile(), _history(rows), MONDAY, None)
        assert p["session_type"] == "rest"
        assert any("load" in e["value"].lower() for e in p["evidence"])

    def test_rest_after_three_consecutive_days(self):
        rows = STEADY + [(1, 5.0, 31.0, 148.0), (2, 5.0, 31.0, 148.0),
                         (3, 5.0, 31.0, 148.0)]
        p = prescriber.prescribe(_profile(), _history(rows), MONDAY, None)
        assert p["session_type"] == "rest"

    def test_rest_when_wrecked(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, "wrecked")
        assert p["session_type"] == "rest"

    def test_good_feel_does_not_force_rest(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, "good")
        assert p["session_type"] != "rest"


class TestLongRule:
    def test_long_on_the_last_available_day(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), SATURDAY, None)
        assert p["session_type"] == "long"
        assert p["distance_km"] > 6.0

    def test_no_long_without_base(self):
        p = prescriber.prescribe(_profile(), _history([(2, 5.0, 30.0, 148.0)]),
                                 SATURDAY, None)
        assert p["session_type"] == "easy"

    def test_long_capped_at_previous_longest_plus_ten_percent(self):
        rows = STEADY + [(6, 10.0, 62.0, 150.0)]
        p = prescriber.prescribe(_profile(), _history(rows), SATURDAY, None)
        assert p["distance_km"] <= 11.0


class TestTempoRule:
    def test_tempo_for_time_based_goal(self):
        p = prescriber.prescribe(_profile(goal_type="break_45"),
                                 _history(STEADY), MONDAY, None)
        assert p["session_type"] == "tempo"

    def test_no_tempo_for_distance_goal(self):
        p = prescriber.prescribe(_profile(goal_type="first_10k"),
                                 _history(STEADY), MONDAY, None)
        assert p["session_type"] == "easy"

    def test_no_second_tempo_in_one_week(self):
        rows = STEADY + [(1, 6.0, 28.0, 172.0)]     # a hard effort two days ago
        p = prescriber.prescribe(_profile(goal_type="break_45"),
                                 _history(rows), MONDAY, None)
        assert p["session_type"] == "easy"


class TestEasyDefaults:
    def test_easy_distance_scales_from_recent_mean(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["session_type"] == "easy"
        assert 3.6 <= p["distance_km"] <= 4.8

    def test_pace_band_brackets_recent_easy_pace(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        lo, hi = p["pace_band_s"]
        assert lo < 370 < hi
        assert hi - lo == 20

    def test_hr_cap_from_observed_easy_hr(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["hr_cap"] == 153

    def test_hr_cap_falls_back_to_max_hr_fraction(self):
        p = prescriber.prescribe(_profile(), _history([]), MONDAY, None)
        assert p["hr_cap"] == 148


class TestEnvelope:
    def test_always_has_date_and_evidence(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["date"] == "2026-08-03"
        assert len(p["evidence"]) >= 1
        assert all({"label", "value"} == set(e) for e in p["evidence"])

    def test_short_history_says_so(self):
        p = prescriber.prescribe(_profile(), _history([(1, 5.0, 30.0, 145.0)]),
                                 MONDAY, None)
        assert any("history" in e["value"].lower() for e in p["evidence"])

    def test_week_target_grows_by_ten_percent(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["week"]["target_km"] == pytest.approx(13.2, abs=0.1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_prescriber.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.prescriber'`

- [ ] **Step 3: Write `src/prescriber.py`**

```python
"""The prescriber: decide today's session from recent load, deterministically.

Rules are ordered — rest, long, tempo, easy — and the first match wins. Every
rule also produces the evidence rows the brief shows, so the advice can always
show its work.
"""

from datetime import date, timedelta

import pandas as pd

from src import queries

REST_ACWR = 1.4
MAX_CONSECUTIVE_DAYS = 3
TIME_BASED_GOALS = {"break_45"}
EASY_FRACTION = 0.7
LONG_FACTOR = 1.4
LONG_CAP_GROWTH = 1.10
PACE_BAND_HALF_WIDTH_S = 10
HR_CAP_MARGIN = 5
HR_CAP_FRACTION = 0.78
WEEK_GROWTH = 1.10
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _is_time_based(profile: dict) -> bool:
    if profile.get("goal_type") in TIME_BASED_GOALS:
        return True
    return profile.get("goal_type") == "other" and bool(profile.get("goal_target"))


def _week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def _long_day(days_available: list[str]) -> str | None:
    """The latest available day in the week owns the long run."""
    present = [d for d in DAY_NAMES if d in days_available]
    return present[-1] if present else None


def _hard_effort_this_week(df: pd.DataFrame, today: date) -> bool:
    """A run in the faster 40% of the last 28 days, run since Monday."""
    window = queries.runs_in_window(df, today, 28).dropna(subset=["pace_min_km"])
    if window.empty:
        return False
    threshold = window["pace_min_km"].quantile(0.40)
    start = _week_start(today)
    dates = pd.to_datetime(window["start_time"]).dt.date
    this_week = window[(dates >= start) & (dates <= today)]
    return bool((this_week["pace_min_km"] < threshold).any())


def _long_run_this_week(df: pd.DataFrame, today: date) -> bool:
    mean_dist = queries.mean_run_distance(df, today)
    if mean_dist is None:
        return False
    start = _week_start(today)
    dates = pd.to_datetime(df["start_time"]).dt.date
    this_week = df[(dates >= start) & (dates <= today)]
    if this_week.empty:
        return False
    return bool((this_week["distance_km"] >= mean_dist * 1.25).any())


def prescribe(profile: dict, df: pd.DataFrame, today: date,
              last_feel: str | None) -> dict:
    """Decide today's session. Pure — pass `today` explicitly."""
    days_available = profile.get("days_available") or []
    today_name = DAY_NAMES[today.weekday()]

    ratio = queries.acwr(df, today)
    consecutive = queries.consecutive_run_days(df, today)
    base = queries.weeks_with_min_runs(df, today)
    mean_dist = queries.mean_run_distance(df, today)
    easy_pace_s = queries.median_easy_pace_s(df, today)
    easy_hr = queries.median_easy_hr(df, today)
    longest = queries.longest_run_km(df, today, days=28)

    week_start = _week_start(today)
    km_so_far = float(df[
        (pd.to_datetime(df["start_time"]).dt.date >= week_start)
        & (pd.to_datetime(df["start_time"]).dt.date <= today)
    ]["distance_km"].sum()) if not df.empty else 0.0
    prev_week_km = queries.km_in_window(df, week_start - timedelta(days=1), 7)
    target_km = round(prev_week_km * WEEK_GROWTH, 1)

    evidence: list[dict] = []
    session_type = None
    distance_km = None

    # ── Rule 1: rest ──
    if today_name not in days_available:
        session_type = "rest"
        evidence.append({"label": "Because", "value": f"{today_name} is not a training day"})
    elif ratio is not None and ratio > REST_ACWR:
        session_type = "rest"
        evidence.append({"label": "Because", "value": f"Load ratio {ratio:.2f} — above 1.40"})
    elif consecutive >= MAX_CONSECUTIVE_DAYS:
        session_type = "rest"
        evidence.append({"label": "Because", "value": f"{consecutive} days running in a row"})
    elif last_feel == "wrecked":
        session_type = "rest"
        evidence.append({"label": "Because", "value": "You said the last one wrecked you"})

    # ── Rule 2: long ──
    if session_type is None and base and today_name == _long_day(days_available) \
            and not _long_run_this_week(df, today):
        session_type = "long"
        distance_km = round((mean_dist or 5.0) * LONG_FACTOR, 1)
        if longest:
            distance_km = round(min(distance_km, longest * LONG_CAP_GROWTH), 1)
        evidence.append({"label": "Because", "value": "Week's long run still owed"})

    # ── Rule 3: tempo ──
    if session_type is None and _is_time_based(profile) and base \
            and not _hard_effort_this_week(df, today):
        session_type = "tempo"
        distance_km = round((mean_dist or 5.0) * 0.9, 1)
        evidence.append({"label": "Because", "value": "No hard effort yet this week"})

    # ── Rule 4: easy ──
    if session_type is None:
        session_type = "easy"
        distance_km = round((mean_dist or 5.0) * EASY_FRACTION, 1)
        evidence.append({"label": "Because", "value": "Steady week — bank an easy one"})

    if session_type == "rest":
        pace_band = None
        hr_cap = None
    else:
        pace = easy_pace_s or 360.0
        if session_type == "tempo":
            pace -= 40
        pace_band = [int(pace - PACE_BAND_HALF_WIDTH_S), int(pace + PACE_BAND_HALF_WIDTH_S)]
        if easy_hr is not None:
            hr_cap = int(round(easy_hr + HR_CAP_MARGIN))
        elif profile.get("max_hr"):
            hr_cap = int(round(profile["max_hr"] * HR_CAP_FRACTION))
        else:
            hr_cap = None

    if queries.history_days(df, today) < queries.MIN_HISTORY_DAYS:
        evidence.append({"label": "Note", "value": "Too little history to judge load yet"})
    elif session_type != "rest":
        evidence.append({"label": "Watch for", "value": "Drift in the last third"})

    return {
        "date": today.isoformat(),
        "week_n": today.isocalendar().week,
        "session_type": session_type,
        "distance_km": distance_km,
        "pace_band_s": pace_band,
        "hr_cap": hr_cap,
        "week": {"km_so_far": round(km_so_far, 1), "target_km": target_km},
        "evidence": evidence,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_prescriber.py -v`
Expected: PASS (17 tests)

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/prescriber.py tests/test_prescriber.py
git commit -m "feat(shindo): add rule-based session prescriber"
```

---

## Task 6: Kurosawa's voice

**Files:**
- Create: `app/api/__init__.py`, `app/__init__.py`, `app/api/persona.py`, `app/api/sensei.py`
- Modify: `requirements.txt`
- Test: `tests/test_persona.py`

**Interfaces:**
- Produces:
  - `persona.SYSTEM_PROMPT: str`
  - `persona.PROMPT_VERSION: str`
  - `persona.MODEL: str` (`"claude-opus-5"`)
  - `persona.register_instruction(register: str) -> str` — registers `brief`, `debrief`, `word`, `reply`
  - `persona.extract_instruction(dialogue: str) -> str | None` — final sentence
  - `sensei.stream_voice(register: str, payload: dict, memory: list[str], question: str | None = None) -> AsyncIterator[str]`

`sensei.stream_voice` is the single seam the API tests monkeypatch.

- [ ] **Step 1: Add dependencies**

```bash
VIRTUAL_ENV=$PWD/.venv uv pip install "fastapi>=0.115" "anthropic>=0.69" "httpx>=0.27"
```

Append to `requirements.txt`:

```
fastapi>=0.115
uvicorn>=0.30
anthropic>=0.69
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_persona.py`:

```python
"""Tests for app.api.persona — prompt assembly and instruction extraction."""

from app.api import persona


class TestPrompt:
    def test_hard_rules_present(self):
        prompt = persona.SYSTEM_PROMPT.lower()
        assert "only" in prompt and "number" in prompt
        assert "one instruction" in prompt

    def test_model_is_opus_5(self):
        assert persona.MODEL == "claude-opus-5"

    def test_version_is_set(self):
        assert persona.PROMPT_VERSION


class TestRegisters:
    def test_all_four_registers(self):
        for r in ("brief", "debrief", "word", "reply"):
            assert persona.register_instruction(r)

    def test_unknown_register_raises(self):
        try:
            persona.register_instruction("nonsense")
        except ValueError:
            return
        raise AssertionError("expected ValueError")


class TestExtractInstruction:
    def test_takes_final_sentence(self):
        text = "You held the pace. Tomorrow: rest."
        assert persona.extract_instruction(text) == "Tomorrow: rest."

    def test_handles_trailing_bracket(self):
        text = "「 You held the pace. Rest tomorrow. 」"
        assert persona.extract_instruction(text) == "Rest tomorrow."

    def test_none_for_empty(self):
        assert persona.extract_instruction("") is None
        assert persona.extract_instruction("   ") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_persona.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 4: Write the persona**

Create empty `app/__init__.py` and `app/api/__init__.py`.

Create `app/api/persona.py`:

```python
"""Kurosawa: one character, four registers.

The system prompt is deliberately frozen — it is the cached prefix on every
request. Anything that varies per call belongs in the user message.
"""

import re

MODEL = "claude-opus-5"
PROMPT_VERSION = "kurosawa-1"

SYSTEM_PROMPT = """\
You are Kurosawa, the sensei of Shindo — a running dojo. You speak to one \
student about their training.

Your manner: stoic, spare, unsentimental. You have decades behind you and \
nothing to prove. You use the imagery of the blade, the mountain, weather, and \
the road — sparingly, never more than one image per reply. You do not flatter. \
You do not scold theatrically. You notice what actually happened.

You believe consistency outranks speed: "I will not make you fast. I will make \
you consistent. Fast is what consistency looks like after a year."

Hard rules, without exception:
1. Use ONLY the numbers present in the JSON you are given. Never estimate, \
round differently, extrapolate, or invent a figure. If a number is absent, \
speak without it.
2. End with exactly ONE instruction — a single concrete thing to do next. It is \
the last sentence, phrased plainly.

Style: 2-4 sentences. No lists, no headings, no emoji, no markdown. Do not \
greet. Do not restate the numbers as a table — the student can already see \
them on the screen. Speak in English.

You remember what you last told this student. If they ignored it, say so once, \
without heat.\
"""

_REGISTERS = {
    "brief": (
        "Register: THE BRIEF. The student is about to run. You are given today's "
        "prescription. Tell them what today is for and what to hold back on. "
        "End with the instruction for this run."
    ),
    "debrief": (
        "Register: THE DEBRIEF. The run is finished. You are given the verdict. "
        "Name the one thing that actually mattered in it. End with the "
        "instruction for next time."
    ),
    "word": (
        "Register: TODAY'S WORD. One or two sentences only, shown on the home "
        "screen. A principle for today, drawn from the prescription. No numbers "
        "unless they are central. Still end with the instruction."
    ),
    "reply": (
        "Register: REPLY. The student has asked you one question about the run "
        "you just debriefed. Answer it directly, in character, from the same "
        "verdict data. End with one instruction."
    ),
}


def register_instruction(register: str) -> str:
    if register not in _REGISTERS:
        raise ValueError(f"unknown register: {register}")
    return _REGISTERS[register]


def extract_instruction(dialogue: str) -> str | None:
    """The final sentence is the instruction — that is rule 2 of the prompt."""
    cleaned = dialogue.strip().strip("「」").strip()
    if not cleaned:
        return None
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    return sentences[-1] if sentences else None
```

- [ ] **Step 5: Write the Claude wrapper**

Create `app/api/sensei.py`:

```python
"""The only module that talks to Claude.

Everything Kurosawa says is a rendering of JSON the engines already produced.
`stream_voice` is the seam the API tests replace.
"""

import json
import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from app.api import persona

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = AsyncAnthropic()
    return _client


def build_user_message(register: str, payload: dict, memory: list[str],
                       question: str | None) -> str:
    parts = [persona.register_instruction(register), "", json.dumps(payload, indent=2)]
    if memory:
        parts += ["", "What you last told this student, newest first:"]
        parts += [f"- {m}" for m in memory]
    if question:
        parts += ["", f"Their question: {question}"]
    return "\n".join(parts)


async def stream_voice(register: str, payload: dict, memory: list[str],
                       question: str | None = None) -> AsyncIterator[str]:
    """Yield Kurosawa's words as they arrive."""
    client = _get_client()
    async with client.messages.stream(
        model=persona.MODEL,
        max_tokens=1000,
        output_config={"effort": "low"},
        system=[{
            "type": "text",
            "text": persona.SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": build_user_message(register, payload, memory, question),
        }],
    ) as stream:
        async for text in stream.text_stream:
            yield text
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_persona.py -v`
Expected: PASS (8 tests)

- [ ] **Step 7: Commit**

```bash
git add app/__init__.py app/api/__init__.py app/api/persona.py app/api/sensei.py \
        tests/test_persona.py requirements.txt
git commit -m "feat(shindo): add Kurosawa persona and Claude streaming wrapper"
```

---

## Task 7: The API

**Files:**
- Create: `app/api/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `store`, `queries`, `prescriber`, `verdict`, `rank`, `sensei.stream_voice`, `db.load_dataframe`, `db.load_laps_dataframe`
- Produces: HTTP endpoints — `GET /api/today`, `GET /api/session`, `GET /api/brief`, `GET /api/debrief/latest`, `POST /api/debrief/{id}/feel`, `POST /api/debrief/{id}/reply`, `POST /api/sync`

SSE frames are `event: <name>\ndata: <json>\n\n`. Token payloads are `{"t": "..."}` so newlines survive JSON encoding.

- [ ] **Step 1: Write the failing test**

Create `tests/test_api.py`:

```python
"""Tests for app.api.main — routes and SSE framing, with Claude mocked out."""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src import db, store


@pytest.fixture(autouse=True)
def _patch_db_path(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")


@pytest.fixture(autouse=True)
def _mock_sensei(monkeypatch):
    """Replace Claude with three deterministic tokens."""
    async def fake_stream(register, payload, memory, question=None):
        for chunk in ("You held the pace. ", "Not a failure. ", "Rest tomorrow."):
            yield chunk

    from app.api import main as api_main
    monkeypatch.setattr(api_main, "stream_voice", fake_stream)


@pytest.fixture
def client():
    from app.api.main import app
    return TestClient(app)


@pytest.fixture
def seeded():
    """Twelve runs over four weeks, the most recent this morning."""
    now = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    acts = []
    for i in range(12):
        start = now - timedelta(days=i * 2)
        acts.append({
            "activityId": 5000 + i,
            "activityName": "Run",
            "startTimeLocal": start.strftime("%Y-%m-%d %H:%M:%S"),
            "distance": 6000.0, "duration": 2220.0, "calories": 400.0,
            "averageHR": 148.0, "maxHR": 165.0, "averageSpeed": 2.7,
            "elevationGain": 20.0,
            "averageRunningCadenceInStepsPerMinute": 170.0,
        })
    db.save_activities(acts)
    return acts


def _events(response) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event_name, payload) pairs."""
    out, name = [], None
    for line in response.text.splitlines():
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: ") and name:
            out.append((name, json.loads(line[6:])))
    return out


class TestToday:
    def test_shape(self, client, seeded):
        r = client.get("/api/today")
        assert r.status_code == 200
        body = r.json()
        assert "prescription" in body
        assert "streak" in body
        assert "week" in body
        assert len(body["last_7_days"]) == 7

    def test_works_with_empty_database(self, client):
        r = client.get("/api/today")
        assert r.status_code == 200
        assert r.json()["prescription"]["session_type"] in (
            "rest", "easy", "long", "tempo")


class TestSession:
    def test_returns_prescription_detail(self, client, seeded):
        r = client.get("/api/session")
        assert r.status_code == 200
        assert "session_type" in r.json()


class TestBrief:
    def test_streams_prescription_then_tokens_then_done(self, client, seeded):
        r = client.get("/api/brief")
        assert r.status_code == 200
        events = _events(r)
        assert events[0][0] == "prescription"
        assert [n for n, _ in events].count("token") == 3
        assert events[-1][0] == "done"

    def test_second_call_replays_without_calling_claude(self, client, seeded, monkeypatch):
        client.get("/api/brief")

        async def explode(*a, **k):
            raise AssertionError("Claude called on replay")
            yield  # pragma: no cover

        from app.api import main as api_main
        monkeypatch.setattr(api_main, "stream_voice", explode)

        events = _events(client.get("/api/brief"))
        assert events[-1][0] == "done"
        assert "".join(p["t"] for n, p in events if n == "token")


class TestDebrief:
    def test_streams_verdict_then_tokens_then_done(self, client, seeded):
        events = _events(client.get("/api/debrief/latest"))
        assert events[0][0] == "verdict"
        assert events[-1][0] == "done"
        assert events[-1][1]["debrief_id"] > 0

    def test_persists_instruction(self, client, seeded):
        client.get("/api/debrief/latest")
        assert store.recent_instructions() == ["Rest tomorrow."]

    def test_replay_makes_no_second_call(self, client, seeded, monkeypatch):
        first = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]

        async def explode(*a, **k):
            raise AssertionError("Claude called on replay")
            yield  # pragma: no cover

        from app.api import main as api_main
        monkeypatch.setattr(api_main, "stream_voice", explode)

        second = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        assert first == second

    def test_empty_database_is_idle_state(self, client):
        events = _events(client.get("/api/debrief/latest"))
        assert events[0][1]["state"] == "no_new_run"


class TestFeelAndReply:
    def test_feel_once(self, client, seeded):
        did = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        assert client.post(f"/api/debrief/{did}/feel", json={"feel": "good"}).status_code == 200
        assert client.post(f"/api/debrief/{did}/feel", json={"feel": "flat"}).status_code == 409

    def test_feel_rejects_unknown_value(self, client, seeded):
        did = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        r = client.post(f"/api/debrief/{did}/feel", json={"feel": "amazing"})
        assert r.status_code == 422

    def test_reply_once(self, client, seeded):
        did = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        r = client.post(f"/api/debrief/{did}/reply", json={"question": "Why?"})
        assert r.status_code == 200
        assert [n for n, _ in _events(r)].count("token") == 3
        again = client.post(f"/api/debrief/{did}/reply", json={"question": "Again?"})
        assert again.status_code == 409

    def test_reply_unknown_debrief_is_404(self, client):
        assert client.post("/api/debrief/999/reply", json={"question": "?"}).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.api.main'`

- [ ] **Step 3: Write `app/api/main.py`**

```python
"""Shindo API — serves engine JSON and streams Kurosawa's voice.

Every endpoint works without Claude: the JSON comes from the engines, and the
dialogue degrades to a fixed line if the API is unavailable.
"""

import json
from collections.abc import AsyncIterator
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src import db, prescriber, queries, rank, store, verdict
from app.api.persona import MODEL, PROMPT_VERSION, extract_instruction
from app.api.sensei import stream_voice

app = FastAPI(title="Shindo")

FALLBACK_LINE = "「 The wind carries no words today. 」"
VALID_FEELS = {"strong", "good", "flat", "wrecked"}


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _frames() -> tuple:
    return db.load_dataframe(), db.load_laps_dataframe()


def _today() -> date:
    return date.today()


def _latest_run(df) -> dict | None:
    if df.empty:
        return None
    row = df.sort_values("start_time").iloc[-1]
    return {
        "activity_id": int(row["activity_id"]),
        "start_time": row["start_time"].to_pydatetime(),
        "distance_km": float(row["distance_km"]),
        "duration_min": float(row["duration_min"]),
        "pace_min_km": float(row["pace_min_km"]),
        "avg_hr": float(row["avg_hr"]) if row["avg_hr"] == row["avg_hr"] else None,
    }


def _last_feel(df) -> str | None:
    """The subjective check-in from the most recent debriefed run, if any."""
    run = _latest_run(df)
    if run is None:
        return None
    existing = store.get_debrief_by_activity(run["activity_id"])
    return existing["feel"] if existing else None


def _current_prescription(df, today: date) -> dict:
    stored = store.get_prescription(today.isoformat())
    if stored:
        return stored["prescription"]
    return prescriber.prescribe(store.get_profile(), df, today, _last_feel(df))


async def _voice_or_fallback(register, payload, memory, question=None) -> AsyncIterator[str]:
    """Stream Kurosawa, or fall back to a fixed line if Claude is unavailable."""
    try:
        async for chunk in stream_voice(register, payload, memory, question):
            yield chunk
    except Exception:
        yield FALLBACK_LINE


@app.post("/api/sync")
def sync():
    """Incremental Garmin pull. Never blocks the UI — errors are reported, not raised."""
    try:
        from src.client import login, pull_activities
        client = login()
        acts = pull_activities(client, "running", days=30, limit=0)
        db.save_activities(acts)
        return {"ok": True, "fetched": len(acts)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/today")
def today():
    df, _ = _frames()
    now = _today()
    prescription = _current_prescription(df, now)
    stored = store.get_prescription(now.isoformat())

    run_dates = set(df["start_time"].dt.date) if not df.empty else set()
    first = store.first_prescription_date()
    since = date.fromisoformat(first) if first else None

    last_7 = []
    for offset in range(6, -1, -1):
        day = now - timedelta(days=offset)
        km = float(df[df["start_time"].dt.date == day]["distance_km"].sum()) if not df.empty else 0.0
        last_7.append({"date": day.isoformat(), "km": round(km, 1)})

    return {
        "date": now.isoformat(),
        "prescription": prescription,
        "word": stored["word"] if stored else None,
        "streak": rank.streak(run_dates, set(), now, since),
        "week": prescription["week"],
        "last_7_days": last_7,
    }


@app.get("/api/session")
def session():
    df, _ = _frames()
    return _current_prescription(df, _today())


@app.get("/api/brief")
async def brief():
    df, _ = _frames()
    now = _today()
    stored = store.get_prescription(now.isoformat())

    if stored:
        async def replay() -> AsyncIterator[str]:
            yield _sse("prescription", stored["prescription"])
            yield _sse("token", {"t": stored["dialogue"]})
            yield _sse("done", {"prescription_id": stored["id"]})
        return StreamingResponse(replay(), media_type="text/event-stream")

    prescription = _current_prescription(df, now)
    memory = store.recent_instructions()

    async def generate() -> AsyncIterator[str]:
        yield _sse("prescription", prescription)
        collected = []
        async for chunk in _voice_or_fallback("brief", prescription, memory):
            collected.append(chunk)
            yield _sse("token", {"t": chunk})
        dialogue = "".join(collected)
        pid = None
        if dialogue and dialogue != FALLBACK_LINE:
            word = extract_instruction(dialogue) or ""
            pid = store.save_prescription(
                now.isoformat(), prescription, dialogue, word, MODEL, PROMPT_VERSION)
        yield _sse("done", {"prescription_id": pid})

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/debrief/latest")
async def debrief_latest():
    df, laps_df = _frames()
    now = _today()
    run = _latest_run(df)

    if run is None:
        async def idle() -> AsyncIterator[str]:
            yield _sse("verdict", {"state": "no_new_run",
                                   "streak": {"days_since_last": None}})
            yield _sse("done", {"debrief_id": None})
        return StreamingResponse(idle(), media_type="text/event-stream")

    existing = store.get_debrief_by_activity(run["activity_id"])
    if existing:
        async def replay() -> AsyncIterator[str]:
            yield _sse("verdict", existing["verdict"])
            yield _sse("token", {"t": existing["dialogue"]})
            yield _sse("done", {"debrief_id": existing["id"]})
        return StreamingResponse(replay(), media_type="text/event-stream")

    run_date = run["start_time"].date().isoformat()
    stored_p = store.get_prescription(run_date)
    v = verdict.judge(run, df, laps_df, now,
                      stored_p["prescription"] if stored_p else None,
                      store.recent_instructions())
    memory = store.recent_instructions()

    async def generate() -> AsyncIterator[str]:
        yield _sse("verdict", v)
        collected = []
        async for chunk in _voice_or_fallback("debrief", v, memory):
            collected.append(chunk)
            yield _sse("token", {"t": chunk})
        dialogue = "".join(collected)
        did = None
        if dialogue and dialogue != FALLBACK_LINE:
            did = store.save_debrief(
                run["activity_id"], stored_p["id"] if stored_p else None, v,
                dialogue, extract_instruction(dialogue), MODEL, PROMPT_VERSION)
        yield _sse("done", {"debrief_id": did})

    return StreamingResponse(generate(), media_type="text/event-stream")


class FeelIn(BaseModel):
    feel: str

    @field_validator("feel")
    @classmethod
    def known_feel(cls, v: str) -> str:
        if v not in VALID_FEELS:
            raise ValueError(f"feel must be one of {sorted(VALID_FEELS)}")
        return v


@app.post("/api/debrief/{debrief_id}/feel")
def set_feel(debrief_id: int, body: FeelIn):
    if store.get_debrief(debrief_id) is None:
        raise HTTPException(404, "no such debrief")
    if not store.set_feel(debrief_id, body.feel):
        raise HTTPException(409, "feel already recorded")
    return {"ok": True}


class ReplyIn(BaseModel):
    question: str


@app.post("/api/debrief/{debrief_id}/reply")
async def reply(debrief_id: int, body: ReplyIn):
    existing = store.get_debrief(debrief_id)
    if existing is None:
        raise HTTPException(404, "no such debrief")
    if existing["followup_q"] is not None:
        raise HTTPException(409, "follow-up already used")

    memory = store.recent_instructions()

    async def generate() -> AsyncIterator[str]:
        collected = []
        async for chunk in _voice_or_fallback(
            "reply", existing["verdict"], memory, body.question
        ):
            collected.append(chunk)
            yield _sse("token", {"t": chunk})
        answer = "".join(collected)
        if answer and answer != FALLBACK_LINE:
            store.set_followup(debrief_id, body.question, answer)
        yield _sse("done", {"debrief_id": debrief_id})

    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_api.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass

- [ ] **Step 6: Start the server and check it by hand**

```bash
.venv/bin/uvicorn app.api.main:app --reload --port 8000
curl -s localhost:8000/api/today | head -40
curl -sN localhost:8000/api/debrief/latest | head -20
```

Expected: `/api/today` returns JSON with a prescription; the SSE stream emits a `verdict` frame then `token` frames.

- [ ] **Step 7: Commit**

```bash
git add app/api/main.py tests/test_api.py
git commit -m "feat(shindo): add FastAPI routes with SSE-streamed dialogue"
```

---

## Task 8: Frontend scaffold and the Dojo shell

**Files:**
- Create: `app/web/package.json`, `app/web/vite.config.js`, `app/web/tailwind.config.js`, `app/web/postcss.config.js`, `app/web/index.html`, `app/web/src/main.jsx`, `app/web/src/App.jsx`, `app/web/src/styles/tokens.css`, `app/web/src/components/Dojo.jsx`, `app/web/src/components/RailMedia.jsx`, `app/web/src/components/Tile.jsx`, `app/web/src/lib/sse.js`
- Create: `app/web/public/art/` (extract the four storyboard frames)
- Modify: `.gitignore`

- [ ] **Step 1: Scaffold and install**

```bash
mkdir -p app/web && cd app/web
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss@^3 postcss autoprefixer
npx tailwindcss init -p
npm install react-router-dom
cd ../..
```

Append to `.gitignore`:

```
node_modules/
app/web/dist/
```

- [ ] **Step 2: Extract the art frames**

```bash
mkdir -p app/web/public/art
.venv/bin/python - <<'PY'
import base64, json, re
lines = open("docs/superpowers/specs/Shindo-storyboard-1b.html",
             encoding="utf-8", errors="replace").read().split("\n")
assets = json.loads(lines[371].strip().rstrip(";"))
names = {"36e0daa6": "rank-mountain", "4b6cf5e4": "session-route",
         "ba8ef340": "home-sensei", "c945a476": "debrief-runner"}
for key, val in assets.items():
    stem = names.get(key[:8])
    if stem and val["mime"] == "image/jpeg":
        open(f"app/web/public/art/{stem}.jpg", "wb").write(
            base64.b64decode(val["data"]))
        print("wrote", stem)
PY
cp app/web/public/art/home-sensei.jpg app/web/public/art/brief-sensei.jpg
```

These are the Phase 1 posters. Higgsfield `.webm` loops drop in beside them later with matching stems; `RailMedia` picks up the video automatically when it exists.

- [ ] **Step 3: Write the config files**

`app/web/vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
})
```

`app/web/tailwind.config.js`:

```js
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0C0B0A', 'ink-2': '#141210',
        washi: '#F2EDE4', 'washi-2': '#E8DFCD', 'washi-3': '#D6CEC0',
        stone: '#8E8779', 'stone-2': '#6F6759', 'stone-3': '#A79E90',
        gold: '#C9A227', crimson: '#B8382C', jade: '#5B7C6E',
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

`app/web/src/styles/tokens.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --ink:#0C0B0A; --ink-2:#141210;
  --washi:#F2EDE4; --washi-2:#E8DFCD; --washi-3:#D6CEC0;
  --stone:#8E8779; --stone-2:#6F6759; --stone-3:#A79E90;
  --gold:#C9A227; --crimson:#B8382C; --jade:#5B7C6E;
  --dur:200ms; --ease:cubic-bezier(0.2,0,0,1);
}

body { background: var(--ink); color: var(--washi); }

.washi-grain { position: relative; }
.washi-grain::before {
  content:''; position:absolute; inset:0; pointer-events:none; opacity:.5;
  background:
    radial-gradient(circle at 20% 16%, rgba(142,135,121,.16), transparent 46%),
    radial-gradient(circle at 80% 76%, rgba(142,135,121,.13), transparent 42%);
}

@keyframes kenburns { from { transform: scale(1); } to { transform: scale(1.07); } }
.kenburns { animation: kenburns 24s ease-in-out infinite alternate; }
@media (prefers-reduced-motion: reduce) { .kenburns { animation: none; } }
```

`app/web/index.html` — replace the generated body and add the fonts:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Shindō</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:ital,wght@0,400;1,400&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Write the SSE reader**

`app/web/src/lib/sse.js`:

```js
/** Read an SSE stream from fetch. Calls onEvent(name, payload) per frame. */
export async function streamSSE(url, options, onEvent) {
  const res = await fetch(url, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop()

    for (const frame of frames) {
      let name = null
      let data = null
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) name = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (name && data !== null) onEvent(name, JSON.parse(data))
    }
  }
}
```

- [ ] **Step 5: Write the shell components**

`app/web/src/components/RailMedia.jsx`:

```jsx
import { useEffect, useState } from 'react'

/**
 * The sensei rail's art. Plays a Higgsfield loop when one exists for this stem,
 * otherwise shows the poster with a slow ken-burns drift. Honours reduced motion.
 */
export default function RailMedia({ stem, children }) {
  const [hasVideo, setHasVideo] = useState(false)
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (reduced) return
    fetch(`/art/${stem}.webm`, { method: 'HEAD' })
      .then((r) => setHasVideo(r.ok))
      .catch(() => setHasVideo(false))
  }, [stem, reduced])

  return (
    <div className="relative h-full overflow-hidden bg-ink-2">
      {hasVideo ? (
        <video
          className="absolute inset-0 h-full w-full object-cover"
          src={`/art/${stem}.webm`}
          poster={`/art/${stem}.jpg`}
          autoPlay loop muted playsInline
        />
      ) : (
        <img
          className={`absolute inset-0 h-full w-full object-cover ${reduced ? '' : 'kenburns'}`}
          src={`/art/${stem}.jpg`}
          alt=""
        />
      )}
      <div className="absolute inset-x-0 bottom-0 p-5"
           style={{ background: 'linear-gradient(180deg,transparent,rgba(12,11,10,.88) 42%)' }}>
        {children}
      </div>
    </div>
  )
}
```

`app/web/src/components/Dojo.jsx`:

```jsx
import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/', glyph: '神', label: 'Home' },
  { to: '/session', glyph: '◎', label: 'Session' },
  { to: '/brief', glyph: '▤', label: 'Brief' },
  { to: '/debrief', glyph: '◈', label: 'Debrief' },
]

/** The layout law: nav strip, sensei rail, workspace. */
export default function Dojo({ rail, children }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-ink">
      <nav className="flex w-[46px] shrink-0 flex-col items-center gap-4 bg-ink py-4">
        {NAV.map(({ to, glyph, label }) => (
          <NavLink key={to} to={to} end={to === '/'} title={label}
            className={({ isActive }) =>
              `font-serif text-[15px] transition-colors ${
                isActive ? 'text-gold' : 'text-washi/30 hover:text-washi/60'}`}>
            {glyph}
          </NavLink>
        ))}
      </nav>

      <aside className="hidden w-[30%] shrink-0 md:block">{rail}</aside>

      <main className="washi-grain flex-1 overflow-y-auto bg-washi text-ink">
        <div className="relative z-10 p-7">{children}</div>
      </main>
    </div>
  )
}
```

`app/web/src/components/Tile.jsx`:

```jsx
/** A stat on washi paper. Numbers are always mono. */
export default function Tile({ label, value, unit }) {
  return (
    <div className="flex flex-1 flex-col gap-2 rounded-md border border-ink/10
                    bg-white/40 px-3 py-3">
      <span className="font-sans text-[10px] font-semibold uppercase tracking-[.14em]
                       text-stone">{label}</span>
      <span className="font-mono text-[22px] leading-none text-ink">
        {value}{unit && <span className="ml-1 text-[11px] text-stone">{unit}</span>}
      </span>
    </div>
  )
}
```

- [ ] **Step 6: Wire the router with stub screens**

`app/web/src/main.jsx`:

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './styles/tokens.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter><App /></BrowserRouter>
  </React.StrictMode>,
)
```

`app/web/src/App.jsx`:

```jsx
import { Route, Routes } from 'react-router-dom'
import Dojo from './components/Dojo.jsx'
import RailMedia from './components/RailMedia.jsx'

function Stub({ name, stem }) {
  return (
    <Dojo rail={
      <RailMedia stem={stem}>
        <p className="font-serif italic text-washi">Kurosawa waits.</p>
      </RailMedia>
    }>
      <h1 className="font-serif text-2xl">{name}</h1>
    </Dojo>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Stub name="Home" stem="home-sensei" />} />
      <Route path="/session" element={<Stub name="Session" stem="session-route" />} />
      <Route path="/brief" element={<Stub name="Brief" stem="brief-sensei" />} />
      <Route path="/debrief" element={<Stub name="Debrief" stem="debrief-runner" />} />
    </Routes>
  )
}
```

- [ ] **Step 7: Verify by eye**

```bash
cd app/web && npm run dev
```

Open http://localhost:5173. Expected: dark nav strip with four glyphs (active one gold), the ronin frame filling the rail with a slow drift and "Kurosawa waits." over a gradient, and a cream workspace with the screen name. Clicking the glyphs swaps the rail art.

- [ ] **Step 8: Commit**

```bash
git add app/web .gitignore
git commit -m "feat(shindo): scaffold Vite frontend with Dojo shell and rail art"
```

---

## Task 9: Home (beat 04)

**Files:**
- Create: `app/web/src/screens/Home.jsx`
- Modify: `app/web/src/App.jsx`

**Interfaces:**
- Consumes: `GET /api/today` → `{date, prescription, word, streak, week, last_7_days}`

- [ ] **Step 1: Write the screen**

`app/web/src/screens/Home.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'
import Tile from '../components/Tile.jsx'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function fmtPace(seconds) {
  if (!seconds) return '—'
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

export default function Home() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/today')
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  if (error) return <Dojo rail={<RailMedia stem="home-sensei" />}>
    <p className="font-sans text-crimson">{error}</p></Dojo>
  if (!data) return <Dojo rail={<RailMedia stem="home-sensei" />}>
    <p className="font-sans text-stone">…</p></Dojo>

  const p = data.prescription
  const maxKm = Math.max(...data.last_7_days.map((d) => d.km), 1)
  const isRest = p.session_type === 'rest'

  return (
    <Dojo rail={
      <RailMedia stem="home-sensei">
        <div className="font-sans text-[10px] font-semibold uppercase
                        tracking-[.16em] text-washi/60">Today's word</div>
        <p className="mt-2 font-serif italic leading-relaxed text-washi">
          {data.word || 'Slow enough to speak. Anything faster is borrowing from tomorrow.'}
        </p>
      </RailMedia>
    }>
      <div className="flex items-baseline gap-3">
        <span className="font-sans text-[10px] font-semibold uppercase
                         tracking-[.16em] text-stone">
          {DAYS[new Date(data.date).getDay() === 0 ? 6 : new Date(data.date).getDay() - 1]}
          {' · '}Week {p.week_n}
        </span>
        <span className="ml-auto font-mono text-[11px] text-stone-2">
          {data.streak}-DAY STREAK
        </span>
      </div>

      <h1 className="mt-2 font-serif text-3xl capitalize">
        {isRest ? 'Rest' : `${p.session_type} ${p.distance_km} km`}
      </h1>

      <div className="mt-6 flex gap-3">
        <Tile label="This week" value={data.week.km_so_far} unit="km" />
        <Tile label="Target" value={data.week.target_km} unit="km" />
        <Tile label="Pace band" value={p.pace_band_s
          ? `${fmtPace(p.pace_band_s[0])}–${fmtPace(p.pace_band_s[1])}` : '—'} />
        <Tile label="HR cap" value={p.hr_cap ?? '—'} />
      </div>

      <div className="mt-6 rounded-md border border-ink/10 bg-white/40 p-4">
        <div className="font-sans text-[10px] font-semibold uppercase
                        tracking-[.14em] text-stone">Last 7 days</div>
        <div className="mt-3 flex h-16 items-end gap-2">
          {data.last_7_days.map((d) => (
            <div key={d.date} className="flex-1 rounded-t-sm"
              title={`${d.date} · ${d.km} km`}
              style={{
                height: `${Math.max((d.km / maxKm) * 100, 3)}%`,
                background: d.km > 0 ? 'var(--gold)' : 'var(--stone-3)',
              }} />
          ))}
        </div>
      </div>

      <button onClick={() => navigate(isRest ? '/debrief' : '/session')}
        className="mt-6 w-full rounded-md bg-ink py-3 font-sans text-xs
                   font-semibold uppercase tracking-[.08em] text-washi">
        {isRest ? 'See the last debrief' : 'Start session'}
      </button>
    </Dojo>
  )
}
```

- [ ] **Step 2: Route it**

In `app/web/src/App.jsx`, add `import Home from './screens/Home.jsx'` and replace the `/` route element with `<Home />`.

- [ ] **Step 3: Verify by eye**

With `uvicorn app.api.main:app --port 8000` and `npm run dev` both running, open http://localhost:5173.
Expected: today's prescribed session as the headline, four washi tiles, a 7-bar chart with gold bars on days you ran, and the streak top-right. The rail shows the ronin with today's word.

- [ ] **Step 4: Commit**

```bash
git add app/web/src/screens/Home.jsx app/web/src/App.jsx
git commit -m "feat(shindo): add Home screen (beat 04)"
```

---

## Task 10: Session (beat 05)

**Files:**
- Create: `app/web/src/screens/Session.jsx`
- Modify: `app/web/src/App.jsx`

**Interfaces:**
- Consumes: `GET /api/session` → the prescription dict

- [ ] **Step 1: Write the screen**

`app/web/src/screens/Session.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'

function fmtPace(seconds) {
  if (!seconds) return '—'
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function Row({ label, value }) {
  return (
    <div className="flex items-baseline justify-between border-b border-ink/10 py-3">
      <span className="font-sans text-[13px] text-stone-2">{label}</span>
      <span className="font-mono text-[15px] text-ink">{value}</span>
    </div>
  )
}

export default function Session() {
  const [p, setP] = useState(null)
  const navigate = useNavigate()

  useEffect(() => { fetch('/api/session').then((r) => r.json()).then(setP) }, [])

  if (!p) return <Dojo rail={<RailMedia stem="session-route" />}>
    <p className="font-sans text-stone">…</p></Dojo>

  return (
    <Dojo rail={
      <RailMedia stem="session-route">
        <div className="font-serif text-lg text-washi">Riverside loop</div>
        <div className="mt-1 font-mono text-[11px] text-washi/60">
          {p.distance_km ? `${p.distance_km} km` : 'Rest day'}
        </div>
      </RailMedia>
    }>
      <div className="flex items-baseline gap-3">
        <button onClick={() => navigate('/')}
          className="font-sans text-[13px] text-stone-2">← Today</button>
        <span className="ml-auto font-sans text-[10px] font-semibold uppercase
                         tracking-[.16em] text-stone">Week {p.week_n}</span>
      </div>

      <h1 className="mt-2 font-serif text-2xl capitalize">
        {p.session_type === 'rest'
          ? 'Rest — no session today'
          : `${p.session_type} ${p.distance_km} km`}
      </h1>

      <div className="mt-6">
        <Row label="Distance" value={p.distance_km ? `${p.distance_km} km` : '—'} />
        <Row label="Pace band" value={p.pace_band_s
          ? `${fmtPace(p.pace_band_s[0])}–${fmtPace(p.pace_band_s[1])} /km` : '—'} />
        <Row label="Heart rate cap" value={p.hr_cap ? `${p.hr_cap} bpm` : '—'} />
        <Row label="This week" value={`${p.week.km_so_far} / ${p.week.target_km} km`} />
      </div>

      {p.session_type !== 'rest' && (
        <button onClick={() => navigate('/brief')}
          className="mt-7 w-full rounded-md bg-ink py-3 font-sans text-xs
                     font-semibold uppercase tracking-[.08em] text-washi">
          Kurosawa speaks first
        </button>
      )}
    </Dojo>
  )
}
```

- [ ] **Step 2: Route it**

In `App.jsx`, add `import Session from './screens/Session.jsx'` and use `<Session />` for `/session`.

- [ ] **Step 3: Verify by eye**

Open http://localhost:5173/session. Expected: the willow-path frame in the rail, a spec-sheet of four rows, and a button through to the brief. On a rest day the button is absent.

- [ ] **Step 4: Commit**

```bash
git add app/web/src/screens/Session.jsx app/web/src/App.jsx
git commit -m "feat(shindo): add Session screen (beat 05)"
```

---

## Task 11: Brief (beat 06)

**Files:**
- Create: `app/web/src/screens/Brief.jsx`
- Modify: `app/web/src/App.jsx`

**Interfaces:**
- Consumes: `GET /api/brief` (SSE) — `prescription` → `token`* → `done`
- Consumes: `streamSSE` from `lib/sse.js`

- [ ] **Step 1: Write the screen**

`app/web/src/screens/Brief.jsx`:

```jsx
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'
import { streamSSE } from '../lib/sse.js'

export default function Brief() {
  const [prescription, setPrescription] = useState(null)
  const [text, setText] = useState('')
  const [streaming, setStreaming] = useState(true)
  const navigate = useNavigate()
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return          // StrictMode double-mount guard
    started.current = true
    streamSSE('/api/brief', {}, (name, payload) => {
      if (name === 'prescription') setPrescription(payload)
      else if (name === 'token') setText((t) => t + payload.t)
      else if (name === 'done') setStreaming(false)
    }).catch(() => setStreaming(false))
  }, [])

  return (
    <Dojo rail={
      <RailMedia stem="brief-sensei">
        <div className="font-sans text-[10px] font-semibold uppercase
                        tracking-[.16em] text-washi/60">The brief · 20 seconds</div>
        <p className="mt-2 font-serif italic leading-relaxed text-washi">
          {text}
          {streaming && <span className="ml-0.5 inline-block h-4 w-[7px]
                                         animate-pulse bg-gold align-[-2px]" />}
        </p>
      </RailMedia>
    }>
      <h1 className="font-serif text-2xl">Before you go</h1>

      {prescription && (
        <div className="mt-6 space-y-3">
          {prescription.evidence.map((e, i) => (
            <div key={i} className="flex items-baseline justify-between
                                    rounded-md border border-ink/10 bg-white/40 px-4 py-3">
              <span className="font-sans text-[10px] font-semibold uppercase
                               tracking-[.14em] text-stone">{e.label}</span>
              <span className="font-sans text-[13px] text-ink">{e.value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-7 flex gap-3">
        <button onClick={() => navigate('/debrief')}
          className="flex-1 rounded-md bg-ink py-3 font-sans text-xs font-semibold
                     uppercase tracking-[.08em] text-washi">Begin the run</button>
        <button onClick={() => navigate('/')}
          className="flex-1 rounded-md border border-ink/20 py-3 font-sans text-xs
                     font-semibold uppercase tracking-[.08em] text-ink">Skip</button>
      </div>
    </Dojo>
  )
}
```

- [ ] **Step 2: Route it**

In `App.jsx`, add `import Brief from './screens/Brief.jsx'` and use `<Brief />` for `/brief`.

- [ ] **Step 3: Verify by eye**

Open http://localhost:5173/brief with `ANTHROPIC_API_KEY` set in the API process.
Expected: the evidence rows appear immediately (they come from the engine), and Kurosawa's words type out on the rail with a gold cursor. Reload — the second load replays instantly from storage with no API call.

- [ ] **Step 4: Commit**

```bash
git add app/web/src/screens/Brief.jsx app/web/src/App.jsx
git commit -m "feat(shindo): add Brief screen with streamed dialogue (beat 06)"
```

---

## Task 12: Debrief (beat 07)

**Files:**
- Create: `app/web/src/screens/Debrief.jsx`
- Modify: `app/web/src/App.jsx`

**Interfaces:**
- Consumes: `GET /api/debrief/latest` (SSE) — `verdict` → `token`* → `done {debrief_id}`
- Consumes: `POST /api/debrief/{id}/feel` and `POST /api/debrief/{id}/reply` (SSE)

- [ ] **Step 1: Write the screen**

`app/web/src/screens/Debrief.jsx`:

```jsx
import { useEffect, useRef, useState } from 'react'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'
import Tile from '../components/Tile.jsx'
import { streamSSE } from '../lib/sse.js'

const FEELS = ['strong', 'good', 'flat', 'wrecked']

function fmtPace(seconds) {
  if (!seconds) return '—'
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function fmtDuration(seconds) {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  return `${m}:${String(seconds % 60).padStart(2, '0')}`
}

export default function Debrief() {
  const [verdict, setVerdict] = useState(null)
  const [text, setText] = useState('')
  const [streaming, setStreaming] = useState(true)
  const [debriefId, setDebriefId] = useState(null)
  const [feel, setFeel] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [asked, setAsked] = useState(false)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    streamSSE('/api/debrief/latest', {}, (name, payload) => {
      if (name === 'verdict') setVerdict(payload)
      else if (name === 'token') setText((t) => t + payload.t)
      else if (name === 'done') { setDebriefId(payload.debrief_id); setStreaming(false) }
    }).catch(() => setStreaming(false))
  }, [])

  async function recordFeel(value) {
    setFeel(value)
    await fetch(`/api/debrief/${debriefId}/feel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feel: value }),
    })
  }

  async function ask() {
    if (!question.trim() || asked) return
    setAsked(true)
    await streamSSE(`/api/debrief/${debriefId}/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }, (name, payload) => {
      if (name === 'token') setAnswer((a) => a + payload.t)
    })
  }

  const rail = (
    <RailMedia stem="debrief-runner">
      <div className="font-sans text-[10px] font-semibold uppercase
                      tracking-[.16em] text-washi/60">The debrief</div>
      <p className="mt-2 font-serif italic leading-relaxed text-washi">
        {text}
        {streaming && <span className="ml-0.5 inline-block h-4 w-[7px]
                                       animate-pulse bg-gold align-[-2px]" />}
      </p>
      {answer && <p className="mt-4 border-t border-washi/20 pt-3 font-serif
                               italic leading-relaxed text-washi/90">{answer}</p>}
    </RailMedia>
  )

  if (verdict?.state === 'no_new_run') {
    return <Dojo rail={rail}>
      <h1 className="font-serif text-2xl">No run yet</h1>
      <p className="mt-3 font-sans text-[14px] text-stone-2">
        Nothing new since the last debrief. The road is still there.</p>
    </Dojo>
  }

  if (!verdict) return <Dojo rail={rail}>
    <p className="font-sans text-stone">…</p></Dojo>

  const r = verdict.run
  const band = verdict.vs_prescription?.pace
  const maxPace = Math.max(...(r.laps.length ? r.laps.map((l) => l.pace_s) : [1]))

  return (
    <Dojo rail={rail}>
      <div className="flex items-baseline gap-3">
        <span className="font-sans text-[10px] font-semibold uppercase
                         tracking-[.16em] text-stone">Session complete · {r.date}</span>
        <span className="ml-auto">
          <span className="font-mono text-[30px] text-ink">{r.km}</span>
          <span className="ml-1 font-sans text-[10px] font-semibold uppercase
                           tracking-[.14em] text-stone">km</span>
        </span>
      </div>

      <div className="mt-5 flex gap-3">
        <Tile label="Time" value={fmtDuration(r.duration_s)} />
        <Tile label="Pace" value={fmtPace(r.pace_s)} />
        <Tile label="Avg HR" value={r.avg_hr ?? '—'} />
      </div>

      {r.laps.length > 0 && (
        <div className="mt-5 rounded-md border border-ink/10 bg-white/40 p-4">
          <div className="flex items-baseline">
            <span className="font-sans text-[10px] font-semibold uppercase
                             tracking-[.14em] text-stone">Pace per km</span>
            {band && <span className="ml-auto font-mono text-[10px] text-stone">
              {band.replace('_', ' ').toUpperCase()}</span>}
          </div>
          <div className="mt-3 flex h-14 items-end gap-1.5">
            {r.laps.map((l, i) => (
              <div key={i} className="flex-1 rounded-t-sm"
                title={`km ${i + 1} · ${fmtPace(l.pace_s)}`}
                style={{
                  height: `${(l.pace_s / maxPace) * 100}%`,
                  background: l.pace_s === maxPace ? 'var(--gold)' : 'var(--stone-3)',
                }} />
            ))}
          </div>
        </div>
      )}

      {debriefId && !feel && (
        <div className="mt-6">
          <div className="font-sans text-[10px] font-semibold uppercase
                          tracking-[.14em] text-stone">How did it feel?</div>
          <div className="mt-3 flex gap-2">
            {FEELS.map((f) => (
              <button key={f} onClick={() => recordFeel(f)}
                className="flex-1 rounded-md border border-ink/20 py-2 font-sans
                           text-[12px] capitalize text-ink hover:bg-ink/5">{f}</button>
            ))}
          </div>
        </div>
      )}
      {feel && <p className="mt-6 font-sans text-[13px] text-stone-2">
        Logged: <span className="text-ink">{feel}</span>. It shapes tomorrow's brief.</p>}

      {debriefId && !asked && (
        <div className="mt-6 flex gap-2">
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask()}
            placeholder="Ask him one thing…"
            className="flex-1 rounded-md border border-ink/20 bg-white/50 px-3
                       py-2 font-sans text-[13px] text-ink outline-none" />
          <button onClick={ask}
            className="rounded-md border border-gold px-4 font-sans text-[11px]
                       font-semibold uppercase tracking-[.14em] text-gold">Ask</button>
        </div>
      )}
    </Dojo>
  )
}
```

- [ ] **Step 2: Route it**

In `App.jsx`, add `import Debrief from './screens/Debrief.jsx'` and use `<Debrief />` for `/debrief`. The file no longer needs the `Stub` helper — delete it.

- [ ] **Step 3: Verify by eye**

Open http://localhost:5173/debrief.
Expected: the runner frame in the rail with Kurosawa's debrief typing out; distance headline, three tiles, and a per-km bar chart if the run has laps. Pick a feel — it disappears and confirms. Ask one question — the answer streams in beneath his debrief, and the input disappears.

- [ ] **Step 4: Full-suite regression**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add app/web/src/screens/Debrief.jsx app/web/src/App.jsx
git commit -m "feat(shindo): add Debrief screen with feel and follow-up (beat 07)"
```

---

## Task 13: Run script and README

**Files:**
- Create: `run-shindo.sh`
- Modify: `README.md`

- [ ] **Step 1: Write the launcher**

`run-shindo.sh`:

```bash
#!/usr/bin/env bash
# Start the Shindo API and web dev server together.
set -euo pipefail
cd "$(dirname "$0")"

.venv/bin/uvicorn app.api.main:app --reload --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

npm --prefix app/web run dev
```

```bash
chmod +x run-shindo.sh
```

- [ ] **Step 2: Document it**

Add to `README.md` after the Dashboard section:

```markdown
## Shindō (the sensei app)

A running dojo with a master in it — Kurosawa briefs you before every run and
debriefs you after, from your own Garmin history.

```bash
# One-time: install Python and JS dependencies
VIRTUAL_ENV=$PWD/.venv uv pip install -r requirements.txt
npm --prefix app/web install

# Add ANTHROPIC_API_KEY to .env, then:
./run-shindo.sh
```

API on :8000, web on :5173. Every screen works without Claude — his voice
degrades to a fixed line while the numbers keep rendering.

See `docs/superpowers/specs/2026-07-31-shindo-design.md` for the full design.
```

- [ ] **Step 3: Verify**

```bash
./run-shindo.sh
```
Expected: both servers start; http://localhost:5173 loads Home.

- [ ] **Step 4: Commit**

```bash
git add run-shindo.sh README.md
git commit -m "docs(shindo): add launcher script and README section"
```

---

## Phase 1 done when

- `.venv/bin/python -m pytest -q` is green, including the pre-existing suite
- `./run-shindo.sh` serves all four screens against your real 39 runs
- A debrief persists, remembers its instruction, accepts one feel and one follow-up
- Killing `ANTHROPIC_API_KEY` degrades every screen to the fallback line without breaking a number
