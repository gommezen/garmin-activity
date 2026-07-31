# Ronin Training Buddy — Design Spec (v1: Post-Run Debrief)

**Date:** 2026-07-31
**Status:** Approved design, pending implementation plan
**Repo:** garmin-activity (monorepo decision — see Decisions)

## Summary

An animated training-buddy app: a stoic ronin character (original design; Blue Eye
Samurai palette/drama × Ninja Scroll stillness/composition) who debriefs each run
against the runner's full training history. A deterministic metrics engine computes
the verdict; Claude renders it in the ronin's voice, streamed live. Debriefs are
persisted append-only so the character has memory.

## Decisions (from brainstorm, 2026-07-31)

| Decision | Choice | Why |
|---|---|---|
| v1 core moment | Post-run debrief | Richest data moment; ~1 year of runs already in DB. Pre-run briefing is v2; mode selection later. |
| Coaching brain | Metrics judge + Claude voices | Deterministic verdict is testable and never invents numbers; LLM does character only. |
| Repo | `garmin-activity`, `app/` folder | Repo owns schema, DB, OAuth tokens; imports beat env-path wiring. Streamlit stays as quick-look tool. |
| Scope tier | "Living debrief" (B) | SSE streaming + append-only memory + one follow-up. A (thin slice) would feel like a report; retrofitting streaming later is costlier. |
| Art source | AI-generated via Higgsfield, dedicated session | Original ronin keeps repo shareable; reference frames stay gitignored. Animation tier decided by what generations yield — v1 assumes portrait + CSS ambient motion. |
| Voice language | English | Assumed; flag if Danish preferred. |
| LLM | `claude-opus-5`, effort `low`, streaming | Persona rendering isn't heavy reasoning; low effort keeps latency snappy. Cost per debrief ≪ $0.01. |

## Non-goals (v1)

Pre-run briefing · mode selection UI · pose states / full animation · TTS · Danish ·
MCP `garmin_debrief` tool · refactoring the remaining ~2000 lines of `ui/dashboard.py`.
The debriefs table is deliberately the substrate for the v2 briefing.

## The experience

One full-bleed scene, no tabs:

1. Ronin portrait (generated art), ambient CSS motion — drifting dust, subtle
   breathing scale, cloth sway. Vermilion-sky palette.
2. Thin stats strip under the portrait: `distance · pace · avg HR · Δ vs 4-week self`.
   Rendered instantly from the verdict JSON (local, no LLM dependency).
3. Dialogue types out token-by-token as Claude streams. Bracketed 「 」 styling.
4. One reply input + Ask button. One follow-up per debrief, answered in character.

Opening the app without a new run triggers the `no_new_run` idle scene (in-character
scolding with days-since-last-run).

## Architecture

```
app/web  (Vite + React + Tailwind)
   │  fetch + ReadableStream over SSE endpoints
   ▼
app/api  (FastAPI, async)
   ├─ sync     → src/client.py    (existing Garmin token cache; resume-only)
   ├─ verdict  → src/queries.py   (NEW) + src/stats.py (existing)
   ├─ voice    → Claude API       (AsyncAnthropic, streamed)
   └─ memory   → debriefs table   (append-only, garmin_data.db)
```

- `src/queries.py` is extracted **only as far as the verdict engine needs**: latest
  run + laps, rolling 4-week averages, weekly load, best-effort/PR detection
  (reusing the sliding-window lap logic), gap/streak queries.
- Frontend dev: Vite proxy `/api` → `localhost:8000`. Single client streaming
  pattern: `fetch()` + ReadableStream (works for both GET and POST SSE endpoints;
  no EventSource).
- `ANTHROPIC_API_KEY` joins the existing gitignored `.env`.

## Verdict engine (deterministic, no LLM)

Pure functions over the DB. Output schema:

```json
{
  "state": "new_run",                    // "new_run" | "no_new_run"
  "run":   {"km": 12.3, "pace_s_per_km": 342, "avg_hr": 162, "duration_s": 4210,
             "laps": [{"km": 1.0, "pace_s": 335, "hr": 158}, ...]},
  "vs_self": {"pace_vs_4wk_pct": 4.0, "dist_vs_avg_km": 1.8,
               "hr_at_pace": "normal"},   // "low" | "normal" | "elevated"
  "flags": ["third_run_this_week", "negative_split"],
  "assessment": "solid",                  // see mapping below
  "streak": {"runs_7d": 3, "km_7d": 31.2, "acwr": 1.15,
              "days_since_last": 2},
  "last_instructions": ["rest tomorrow", "..."],  // ≤3, newest first
  "prs": []                               // best-effort hits this run, if any
}
```

**Assessment mapping (ordered, first match wins):**

1. `caution` — ACWR > 1.4, or HR elevated at easy pace, or distance > 1.6× 4-week avg
2. `excellent` — PR/best-effort hit, or pace ≥ 3% better than 4-week avg at normal HR
3. `easy` — pace ≥ 5% slower than 4-week avg and HR low/normal (recovery run)
4. `solid` — everything else

**ACWR** = acute:chronic workload ratio = (km last 7 days) / (mean weekly km over
last 28 days). Guard: requires ≥ 14 days of history, else omitted and no caution
from this rule.

**Flags (v1 set):** `pr_hit`, `negative_split`, `third_run_this_week` (or
`nth_run_this_week`), `load_spike`, `long_gap` (> 7 days since previous run),
`longest_run_4wk`.

`no_new_run` state carries only `streak` + `last_instructions`.

## The ronin's voice (Claude)

- **SDK:** `anthropic.AsyncAnthropic`, `client.messages.stream(...)`,
  model `claude-opus-5`, `output_config={"effort": "low"}`, `max_tokens=1000`,
  thinking left at default (adaptive). No sampling params.
- **System prompt** (~800 tokens, `cache_control: {"type": "ephemeral"}` — Opus 5
  caches from 512 tokens): character sheet (stoic ronin, terse, blade/wind/mountain
  imagery, English) + two hard rules: *use only numbers present in the verdict
  JSON* and *end with exactly one actionable instruction*. Stored in
  `app/api/persona.py` with `PROMPT_VERSION` constant.
- **User message:** verdict JSON + last ≤3 debrief instructions (his memory).
- **Follow-up turn:** same system prompt + original verdict + first dialogue +
  user question → streamed answer. Exactly one follow-up per debrief (UI-enforced;
  schema stores one q/a pair).

## Data

New table in `garmin_data.db`, created by `src/db.py` next to existing schema:

```sql
CREATE TABLE IF NOT EXISTS debriefs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  activity_id    INTEGER REFERENCES activities(activity_id),  -- NULL for no_new_run
  created_at     TEXT NOT NULL,          -- ISO 8601 UTC
  verdict_json   TEXT NOT NULL,
  dialogue       TEXT NOT NULL,
  instruction    TEXT,                    -- extracted final instruction, for memory
  followup_q     TEXT,
  followup_a     TEXT,
  model          TEXT NOT NULL,
  prompt_version TEXT NOT NULL
);
```

Append-only: no UPDATE/DELETE paths except filling `followup_q/followup_a` once
(the single allowed write-back, guarded by NULL check). `instruction` is parsed
from the dialogue's final line at persist time; if parsing fails, store NULL and
memory degrades gracefully.

## API surface

| Endpoint | Method | Behavior |
|---|---|---|
| `/api/sync` | POST | Run incremental Garmin sync (token cache; no first-login/MFA). Returns `{new_activities: n}`. |
| `/api/debrief/latest` | GET (SSE) | If latest activity has no debrief → generate: event `verdict` (JSON) → events `token` → event `done` `{debrief_id}`. If already debriefed → replay stored verdict + dialogue as the same event sequence (no LLM call). |
| `/api/debrief/{id}/reply` | POST (SSE) | Body `{question}`. Streams `token`* → `done`. 409 if follow-up already used. |

SSE event names: `verdict`, `token`, `done`, `error`.

## Error handling

| Failure | Behavior |
|---|---|
| Garmin sync fails | Serve latest stored debrief; non-blocking notice. Sync never gates the UI. |
| Claude down / rate-limited / `stop_reason: refusal` | Stats strip renders from local verdict; static fallback line 「 The wind carries no words today. 」; debrief **not** persisted (retry next open). |
| No new run | `no_new_run` verdict → idle scene (this IS a debrief, persisted with NULL activity_id at most once per calendar day). |
| Dialogue instruction unparseable | Store NULL instruction; memory list just gets shorter. |

Degradation principle: the verdict never depends on Claude — the app always shows
a correct run summary.

## Testing

- **Verdict engine (pytest, the core):** synthetic fixtures — PR run, load-spike
  run (ACWR > 1.4), recovery run, first-run-after-gap, no_new_run, < 14 days
  history (ACWR guard). Assert assessment, flags, and vs_self math.
- **API:** mocked Claude client streaming canned tokens; assert SSE event sequence,
  replay path (no second LLM call), 409 on second follow-up. Schema test for
  `debriefs`.
- **Persona:** not unit-tested; iterated by taste, correlated via `prompt_version`.

## Art pipeline (post-spec)

1. `design/inspiration/` — gitignored; holds the two reference frames (Blue Eye
   Samurai still, Ninja Scroll Jubei) + anything Niels adds.
2. Dedicated Claude + Higgsfield session → original ronin hero portrait
   (+ optional variants). Generated originals live in `app/web/public/art/`
   (committed).
3. Frontend slot `<RoninStage assessment={...}>`: v1 renders one portrait with CSS
   ambient motion; assessment-keyed pose variants slot in later without
   restructuring.

## Run

```
uvicorn app.api.main:app --reload        # API :8000
npm run dev --prefix app/web             # Web :5173, proxies /api
```
