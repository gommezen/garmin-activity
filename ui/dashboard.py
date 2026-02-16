"""Streamlit dashboard for Garmin running activities."""

import sys
from pathlib import Path

# Add project root to path so src/ imports work
sys.path.insert(0, str(Path(__file__).parents[1]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.db import load_dataframe
from src.stats import weekly_summary, monthly_summary, personal_records

st.set_page_config(page_title="Garmin Running", page_icon="🏃", layout="wide")
st.title("🏃 Garmin Running Dashboard")


@st.cache_data(ttl=60)
def load_data():
    return load_dataframe()


def make_chart(df, x, y, title, unit, color="#2196F3"):
    data = df.dropna(subset=[y])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data[x], y=data[y],
        mode="lines+markers",
        marker=dict(size=8, color=color),
        line=dict(color=color, width=2),
        hovertemplate=f"%{{x|%b %d, %Y}}<br><b>%{{y:.1f}} {unit}</b><extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis_title=None, yaxis_title=unit,
        height=350, margin=dict(l=40, r=20, t=40, b=30),
        hovermode="x unified",
    )
    return fig


def make_dual_chart(df, x, y1, y2, title, label1, label2, unit, c1="#E91E63", c2="#9C27B0"):
    data = df.dropna(subset=[y1, y2])
    fig = go.Figure()
    for y, label, color in [(y1, label1, c1), (y2, label2, c2)]:
        fig.add_trace(go.Scatter(
            x=data[x], y=data[y],
            name=label,
            mode="lines+markers",
            marker=dict(size=8, color=color),
            line=dict(color=color, width=2),
            hovertemplate=f"%{{x|%b %d, %Y}}<br><b>{label}: %{{y:.0f}} {unit}</b><extra></extra>",
        ))
    fig.update_layout(
        title=title,
        xaxis_title=None, yaxis_title=unit,
        height=350, margin=dict(l=40, r=20, t=40, b=30),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


df = load_data()

if df.empty:
    st.warning("No data yet. Run `python pull_activities.py running` to pull activities.")
    st.stop()

# --- Latest run summary ---
latest = df.iloc[-1]
st.subheader(f"Latest Run — {latest['start_time'].strftime('%b %d, %Y')}")

cols = st.columns(4)
cols[0].metric("Distance", f"{latest['distance_km']:.2f} km")
cols[1].metric("Duration", f"{int(latest['duration_min'])}:{int(latest['duration_s'] % 60):02d} min")
cols[2].metric("Pace", f"{int(latest['pace_min_km'])}:{int((latest['pace_min_km'] % 1) * 60):02d} /km")
cols[3].metric("Calories", f"{latest['calories']:.0f} kcal")

cols2 = st.columns(4)
if pd.notna(latest["avg_hr"]):
    cols2[0].metric("Avg HR", f"{latest['avg_hr']:.0f} bpm")
if pd.notna(latest["max_hr"]):
    cols2[1].metric("Max HR", f"{latest['max_hr']:.0f} bpm")
if pd.notna(latest["elevation_gain"]):
    cols2[2].metric("Elevation", f"+{latest['elevation_gain']:.0f} m")
if pd.notna(latest["cadence"]):
    cols2[3].metric("Cadence", f"{latest['cadence']:.0f} spm")

st.divider()

# --- Tabs ---
tab_trends, tab_summary = st.tabs(["Trends", "Summary"])

# --- Trends tab ---
with tab_trends:
    st.subheader("Trends Over Time")
    t1, t2, t3, t4 = st.tabs(["Distance & Pace", "Heart Rate", "Effort", "Cadence & Elevation"])

    with t1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_chart(df, "start_time", "distance_km", "Distance", "km", "#2196F3"), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart(df, "start_time", "pace_min_km", "Pace", "min/km", "#FF5722"), use_container_width=True)

    with t2:
        st.plotly_chart(make_dual_chart(df, "start_time", "avg_hr", "max_hr", "Heart Rate", "Avg HR", "Max HR", "bpm"), use_container_width=True)

    with t3:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_chart(df, "start_time", "duration_min", "Duration", "min", "#4CAF50"), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart(df, "start_time", "calories", "Calories", "kcal", "#FF9800"), use_container_width=True)

    with t4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_chart(df, "start_time", "cadence", "Cadence", "spm", "#607D8B"), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart(df, "start_time", "elevation_gain", "Elevation Gain", "m", "#795548"), use_container_width=True)

# --- Summary tab ---
with tab_summary:
    # Personal records
    prs = personal_records(df)
    st.subheader("Personal Records")
    pr_cols = st.columns(3)
    if "fastest_pace" in prs:
        pr = prs["fastest_pace"]
        pr_cols[0].metric("Fastest Pace", pr["value"], f"{pr['distance']} — {pr['date']}")
    if "longest_run" in prs:
        pr = prs["longest_run"]
        pr_cols[1].metric("Longest Run", pr["value"], f"{pr['pace']} — {pr['date']}")
    if "most_elevation" in prs:
        pr = prs["most_elevation"]
        pr_cols[2].metric("Most Elevation", pr["value"], f"{pr['distance']} — {pr['date']}")

    st.divider()

    # Monthly summary
    st.subheader("Monthly Summary")
    monthly = monthly_summary(df)
    monthly.columns = ["Runs", "Total km", "Total min", "Avg Pace", "Avg Cadence", "Avg HR", "Elevation (m)", "Calories"]
    st.dataframe(monthly, use_container_width=True)

    # Weekly summary
    st.subheader("Weekly Summary")
    weekly = weekly_summary(df)
    weekly.columns = ["Runs", "Total km", "Total min", "Avg Pace", "Avg Cadence", "Avg HR", "Elevation (m)", "Calories"]
    st.dataframe(weekly, use_container_width=True)
