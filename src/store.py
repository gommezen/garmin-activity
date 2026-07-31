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
