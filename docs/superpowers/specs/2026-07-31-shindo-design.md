# Shindō — Design Spec

**Date:** 2026-07-31
**Status:** Approved design, pending implementation plan
**Repo:** `garmin-activity` (monorepo — `app/` beside `src/`)
**Supersedes:** `2026-07-31-training-buddy-design.md` (single-screen debrief; folded in as beat 07)

## Summary

A running app with a master in it. **Kurosawa**, a sensei rendered as animated sumi-e
art, briefs you before every run and debriefs you after, drawing on your full Garmin
history. Rank is earned by showing up. Nine screens on a persistent "Dojo" layout:
nav strip · sensei art rail · workspace.

A deterministic engine decides *what to prescribe* and *how the run went*; Claude
renders those decisions in Kurosawa's voice, streamed live. The sensei never invents
a number.

Source of truth for the product shape: `Shindo-storyboard-1b.html` — direction 1b,
"The Dojo — persistent sensei rail."

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Product shape | The nine-beat storyboard | Chosen over the single-screen debrief. Multiple screens with animated visuals. |
| Layout | Dojo (1b): nav · sensei rail · workspace | The storyboard's own layout law. Denser, scales to nine screens, less cinematic than 1a. |
| Plan brain | **Rule-based prescriber** | No periodised multi-week plan. Each day derived from recent load, ACWR, pace trend, rest debt. Deterministic, unit-testable, works on the 39 runs that exist today. |
| Voice | Claude renders, never decides | `claude-opus-5`, effort `low`, streamed over SSE. Numbers come only from the engine. |
| Visuals | **Pre-rendered Higgsfield loops** | Short webm/mp4 per slot, committed as assets. Free at runtime, offline, art-directed deliberately. |
| Build order | **Spine first** | Phase 1 = the daily loop (04·05·06·07) on real data. Then the frame (01·02·02b·03), then depth (08·09). |
| Repo | `garmin-activity`, `app/` | Owns schema, DB, OAuth tokens. Streamlit stays as the quick-look tool. |
| Language | English | Copy in the storyboard is English; Danish is a later i18n pass. |

## The nine beats

| # | Screen | Rail art | Workspace |
|---|---|---|---|
| 01 | First run | Mountain (sumi-e) | SHINDŌ · *"Come. Bring nothing but your shoes."* · three proof points · Begin |
| 02 | Onboarding — set your path | Sensei | Goal (first 10K / break 45 / return / other) · day picker |
| 02b | Onboarding — where you start | Sensei | Level · weekly volume range · recent bests |
| 03 | The sensei's first word | Sensei | The contract: run slow when told, rest when told, tell the truth |
| 04 | Home — today | Sensei + today's word | Today's session · streak · week volume · 7-day chart · Start session |
| 05 | Start a session | Route / landscape | Spec sheet: distance, pace band, HR cap, watch state |
| 06 | Before you go — the brief | Sensei, speaking | 20-second brief + **its evidence** (Because / Watch for) |
| 07 | After — summary & debrief | The runner | Distance · time · pace · HR · per-km chart vs band · **How did it feel?** |
| 08 | Rank progression | Mountain | Grade, sessions to next, lifetime stats, grade history |
| 09 | Profile & settings | Avatar | Three-pane preferences: training · sensei · devices · account |

Copy note: *"Free while you train three times a week"* on 01 is storyboard copy only —
no billing in scope.

## Layout law (Dojo)

```
┌────┬──────────────┬─────────────────────────────┐
│nav │  sensei rail │  workspace                  │
│ 神 │  <video loop>│  panels: stats, charts,     │
│ ◎  │              │  forms, actions             │
│ ▤  │  label       │                             │
│ ◈  │  his word    │                             │
│ ☰  │  (over art)  │                             │
└────┴──────────────┴─────────────────────────────┘
  46px    ~30%              remainder
```

Three regions, fixed for every screen. His current word always lives **on the art**,
never in the workspace. Numbers and controls always live on **washi paper**, never on
the art. Below 900px the rail collapses to a top band and the workspace stacks.

## Design tokens

Lifted from the storyboard file — use verbatim.

```css
--ink:#0C0B0A;  --ink-2:#141210;
--washi:#F2EDE4; --washi-2:#E8DFCD; --washi-3:#D6CEC0;
--stone:#8E8779; --stone-2:#6F6759; --stone-3:#A79E90;
--gold:#C9A227;      /* accent: highlights, active chart bar, active nav */
--crimson:#B8382C;   /* rare: seal, one splash, danger */
--jade:#5B7C6E;      /* success, in-band */
--serif:'Source Serif 4', Georgia, serif;   /* Kurosawa's voice, italic */
--sans:'Inter', ui-sans-serif, system-ui;    /* labels, UI */
--mono:'JetBrains Mono', ui-monospace, monospace; /* every number */
--dur:200ms; --ease:cubic-bezier(0.2,0,0,1);
```

Radii 2/3/6/8/12px; spacing scale 4px-based (4·8·12·16·20·24·32·40·48·64).

## Art pipeline

1. `design/inspiration/` — gitignored; reference frames (Ninja Scroll, Blue Eye
   Samurai, the four storyboard frames).
2. Dedicated Higgsfield session per slot. **Generate to the slot's aspect ratio** so
   nothing is cropped: rail slots **3:4**, full-bleed slots **16:9**.
3. Output to `app/web/public/art/`, committed:

| File | Slot | Aspect | Phase |
|---|---|---|---|
| `home-sensei.webm` | 04 rail | 3:4 | 1 |
| `session-route.webm` | 05 rail — the willow path | 3:4 | 1 |
| `brief-sensei.webm` | 06 rail — sensei speaking | 3:4 | 1 |
| `debrief-runner.webm` | 07 rail — the runner | 3:4 | 1 |
| `splash-mountain.webm` | 01 full-bleed | 16:9 | 2 |
| `onboarding-sensei.webm` | 02/02b rail | 3:4 | 2 |
| `firstword-sensei.webm` | 03 rail | 3:4 | 2 |
| `rank-mountain.webm` | 08 rail | 3:4 | 3 |
| `avatar.jpg` | 09 | 1:1 | 3 |

4. Each `.webm` ships with a `.jpg` poster (first frame). Rendered as
   `<video autoplay loop muted playsinline poster="…">`. Under
   `prefers-reduced-motion: reduce`, the poster is shown and the video is not loaded.
5. Target ≤ 4s loop, ≤ 1.5 MB each.

## Architecture

```
app/web  (Vite + React + Tailwind)   fetch + ReadableStream over SSE
   ▼
app/api  (FastAPI, async)
   ├─ sync       → src/client.py    (existing token cache; resume-only)
   ├─ prescribe  → src/prescriber.py (NEW — rules)      ─┐
   ├─ judge      → src/verdict.py    (NEW — rules)       ├─ both on src/queries.py (NEW)
   ├─ rank       → src/rank.py       (NEW — derived)    ─┘   + src/stats.py (existing)
   ├─ voice      → app/api/sensei.py (Claude, streamed)
   └─ store      → profile · prescriptions · debriefs (append-only, garmin_data.db)
```

`src/queries.py` is extracted from `ui/dashboard.py` only as far as these engines
need: runs in window, laps, rolling averages, weekly load, best efforts, gaps.
The remaining dashboard refactor is **not** in scope.

## The prescriber (rules — beats 04, 05, 06)

Inputs: profile (goal, available days), last 28 days of runs, today's date, last
debrief's subjective feel.

Output — `prescription.json`:

```json
{
  "date": "2026-08-03", "week_n": 4,
  "session_type": "easy",              // easy | long | tempo | rest
  "distance_km": 6.0,
  "pace_band_s": [360, 380],
  "hr_cap": 148,
  "week": {"km_so_far": 28.0, "target_km": 34.0},
  "evidence": [
    {"label": "Because",   "value": "3 of 3 runs above band"},
    {"label": "Watch for", "value": "Drift after km 4"}
  ],
  "word": "Slow enough to speak. Anything faster is borrowing from tomorrow."
}
```

**Rules, ordered — first match wins:**

1. `rest` — today not in available days · OR ACWR > 1.4 · OR 3 consecutive run-days ·
   OR last feel was `wrecked`
2. `long` — today is the week's designated long day (latest available day) and no long
   run yet this week and **base established**
3. `tempo` — goal is **time-based**, base established, none yet this week (max 1/week)
4. `easy` — otherwise

**Definitions:**
- **base established** = ≥ 2 runs per week for 3 consecutive weeks.
- **time-based goal** = `break_45` or any `other` goal carrying a target time.
  `first_10k` and `return_to_running` are not time-based — they never get tempo.
- **feel** (set on the debrief, one of): `strong` · `good` · `flat` · `wrecked`.

**Derivations:**
- ACWR = km(last 7d) ÷ mean weekly km(last 28d). Requires ≥ 14 days history, else
  omitted and rule 1 cannot fire on it.
- easy distance = 0.6–0.8 × mean run distance (28d); long = 1.3–1.5 ×, capped at
  previous longest + 10%.
- pace band = median easy-run pace (28d) ± 10 s/km.
- HR cap = median easy-run HR (28d) + 5 bpm. Fallback when there is no easy-run
  history: `0.78 × profile.max_hr`. `max_hr` is asked for in onboarding (02b) and
  defaults to the highest HR observed across all stored activities.
- weekly target = previous week km × 1.1, clamped so projected ACWR ≤ 1.3.

**Evidence rows** are generated by the rule that fired — the brief always shows why.

## The judge (rules — beat 07)

Output — `verdict.json`: run + laps, `vs_self` (pace vs 4-week, distance vs average,
HR at pace), `vs_prescription` (in band / above / below, distance delivered), flags
(`pr_hit`, `negative_split`, `drift_after_km_n`, `load_spike`, `long_gap`,
`longest_run_4wk`), `assessment` (`caution` | `excellent` | `easy` | `solid`),
`streak`, `last_instructions` (≤ 3).

Assessment order: `caution` (ACWR > 1.4 · HR elevated at easy pace · distance > 1.6×
average) → `excellent` (PR/best effort · pace ≥ 3% better at normal HR) → `easy`
(≥ 5% slower with low/normal HR) → `solid`.

**Streak** = consecutive days that were either a run or a **prescribed** rest day. A
prescribed rest day does not break it; an unscheduled skip does. Because it depends on
prescriptions, the streak counts only from the date of the first prescription — the 39
runs already in the database predate the app and are history, not streak.

## Rank (beat 08)

Derived, never stored. **A grade is a combination of three dimensions — consistency,
speed, and distance — and all three must be met.** You cannot buy a grade with volume
alone, and a fast runner who never goes long stays where they are.

| Grade | Sessions | Best 5 km pace | Longest run |
|---|---|---|---|
| Shodan · first | 20 | — | 5 km |
| Nidan · second | 50 | 6:30 /km | 8 km |
| Sandan · third | 100 | 6:00 /km | 12 km |
| Yondan · fourth | 160 | 5:40 /km | 16 km |
| Godan · fifth | 230 | 5:20 /km | 21.1 km |
| Rokudan · sixth | 310 | 5:00 /km | 30 km |

Grade = the highest row where **all three** columns are satisfied. The rank screen
names the blocking dimension ("your distance holds you at second grade") — which gives
Kurosawa something specific to push on, and turns rank into direction rather than a
score.

**Mixed runs count.** Every stored activity counts toward sessions regardless of
intensity or session type, and the speed and distance columns are evaluated as
best-efforts across all runs — an interval session's fast 5 km split counts, a
long run inside a mixed session counts.

> **Open question — cross-training.** If "mixed" is also meant to include non-running
> activities (cycling, walking, hiking), that is a schema change: `activities` has no
> sport-type column today, so the puller would need to store it and history would need
> a re-pull to backfill. Resolve before Phase 3; it does not affect Phase 1.

"Since <date>" = the date the last unmet requirement was satisfied.

## Kurosawa's voice

One persona, four registers — `brief`, `debrief`, `word`, `contract` — selected by an
instruction appended to a shared system prompt (`app/api/persona.py`, with
`PROMPT_VERSION`).

- `claude-opus-5`, `AsyncAnthropic`, `client.messages.stream()`,
  `output_config={"effort": "low"}`, `max_tokens=1000`, adaptive thinking default,
  no sampling params.
- System prompt ~800 tokens with `cache_control: {"type": "ephemeral"}` (Opus 5 caches
  from 512 tokens).
- Two hard rules in the prompt: **use only numbers present in the input JSON**, and
  **end with exactly one instruction**.
- User message: the prescription or verdict JSON + his last ≤3 instructions.
- One follow-up turn allowed per debrief.

## Data

Created by `src/db.py` beside the existing schema. Append-only throughout.

```sql
profile(id=1, display_name, goal_type, goal_target, goal_date, days_available,
        level, weekly_volume_lo, weekly_volume_hi, pb_json, units, max_hr,
        created_at, updated_at)

prescriptions(id, date UNIQUE, prescription_json, brief_dialogue, word,
              model, prompt_version, created_at)

debriefs(id, activity_id → activities, prescription_id → prescriptions NULL,
         verdict_json, dialogue, instruction, feel, followup_q, followup_a,
         model, prompt_version, created_at)
```

`prescription_id` is nullable: a run on an unscheduled day, or any run predating the
app, has no prescription — the verdict then omits `vs_prescription` and the debrief
speaks only to history.

`profile` is the one mutable row (settings). `prescriptions` and `debriefs` are
insert-only, except two guarded one-time fills: `debriefs.feel` and the follow-up pair.

## API

| Endpoint | Method | Behavior |
|---|---|---|
| `/api/sync` | POST | Incremental Garmin pull. Never gates the UI. |
| `/api/today` | GET | Home payload: prescription, word, streak, week volume, 7-day chart, rank. |
| `/api/session` | GET | Today's prescription detail for beat 05. |
| `/api/brief` | GET (SSE) | `prescription` event → `token`* → `done`. Replays stored brief if already generated today. |
| `/api/debrief/latest` | GET (SSE) | `verdict` event → `token`* → `done {debrief_id}`. Replays if already debriefed. |
| `/api/debrief/{id}/feel` | POST | Subjective check-in; feeds tomorrow's prescriber. 409 if already set. |
| `/api/debrief/{id}/reply` | POST (SSE) | `token`* → `done`. 409 if follow-up used. |
| `/api/rank` | GET | Grade, progress, lifetime stats, grade history. |
| `/api/profile` | GET/PUT | Onboarding + settings. |

SSE event names: `prescription` · `verdict` · `token` · `done` · `error`.

## Error handling

| Failure | Behavior |
|---|---|
| Garmin sync fails | Serve stored state; quiet notice. Sync is never blocking. |
| Claude unavailable / rate-limited / `stop_reason: refusal` | All panels render from local JSON; static fallback line 「 The wind carries no words today. 」; nothing persisted, retry on next open. |
| No profile yet | Redirect to onboarding (02). |
| Insufficient history (< 14 days) | Prescriber omits ACWR rules and says so in the evidence row. |
| No new run | Debrief shows the idle state; Home still prescribes. |
| Instruction unparseable | Store NULL; memory list shortens. |

Degradation principle: **every screen works without Claude.** He is the voice, not the
data path.

## Testing

- **`src/prescriber.py`** — the heaviest suite. Fixtures per rule: rest day, ACWR
  spike, 3-consecutive-days, long-run day, tempo eligibility, base-not-established,
  < 14 days history. Assert session type, distance, band, HR cap, evidence rows.
- **`src/verdict.py`** — PR run, load spike, recovery run, in/out of band,
  first-run-after-gap.
- **`src/rank.py`** — streak across prescribed rest days (Phase 1); composite grade
  boundaries, blocking-dimension detection, and grade-since dates (Phase 3).
- **API** — mocked Claude streaming canned tokens; SSE event order, replay path makes
  no second LLM call, 409s on repeat feel/follow-up.
- **Persona** — not unit-tested; iterated by taste, correlated via `prompt_version`.

## Build phases

**Phase 1 — the spine (04 · 05 · 06 · 07).** Dojo shell, nav, animated rail, tokens.
`src/queries.py` extraction, prescriber, verdict, Claude streaming, `prescriptions` +
`debriefs` tables, four art loops. Usable on real runs at the end of this phase.

**Phase 2 — the frame (01 · 02 · 02b · 03).** Profile table, onboarding flow, contract
screen, splash. Prescriber switches from inferred defaults to stated goal.

**Phase 3 — the depth (08 · 09).** Rank, grade history, lifetime stats, three-pane
settings.

The implementation plan that follows this spec covers **Phase 1 only**. Phases 2 and 3
get their own plans, written once Phase 1 is running on real runs — by then the shell,
the engines, and the art pipeline will have taught us things this spec is guessing at.

## Non-goals

Periodised multi-week plans · runtime art generation · TTS · Danish · billing ·
multi-user · MCP `garmin_debrief` tool (free later — same engines) · the remaining
`ui/dashboard.py` refactor.
