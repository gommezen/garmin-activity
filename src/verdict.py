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
        lo, hi = prescription.get("pace_band_s") or [None, None]
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
                run["distance_km"] - (prescription.get("distance_km") or 0), 2),
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
