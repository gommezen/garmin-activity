"""Shindo API — serves engine JSON and streams Kurosawa's voice.

Every endpoint works without Claude: the JSON comes from the engines, and the
dialogue degrades to a fixed line if the API is unavailable.
"""

import json
from collections.abc import AsyncIterator
from datetime import date, timedelta

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src import db, prescriber, rank, store, verdict
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
        # pd.isna, not `x == x`: the self-comparison idiom only catches float
        # NaN. A column that is entirely null comes back as object dtype full
        # of Python None, where `None == None` is True and float(None) raises.
        "avg_hr": None if pd.isna(row["avg_hr"]) else float(row["avg_hr"]),
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
