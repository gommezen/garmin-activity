"""Streamlit dashboard for Garmin running activities."""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from db import DB_PATH, COLUMNS

st.set_page_config(page_title="Garmin Running", page_icon="🏃", layout="wide")
st.title("🏃 Garmin Running Dashboard")


@st.cache_data(ttl=60)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM activities ORDER BY start_time", conn)
    conn.close()
    df.columns = COLUMNS
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["distance_km"] = df["distance_m"] / 1000
    df["duration_min"] = df["duration_s"] / 60
    df["pace_min_km"] = df["duration_min"] / df["distance_km"].replace(0, float("nan"))
    return df


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

# --- Interactive charts ---
st.subheader("Trends Over Time")

tab1, tab2, tab3, tab4 = st.tabs(["Distance & Pace", "Heart Rate", "Effort", "Cadence & Elevation"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart(df, "start_time", "distance_km", "Distance", "km", "#2196F3"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart(df, "start_time", "pace_min_km", "Pace", "min/km", "#FF5722"), use_container_width=True)

with tab2:
    st.plotly_chart(make_dual_chart(df, "start_time", "avg_hr", "max_hr", "Heart Rate", "Avg HR", "Max HR", "bpm"), use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart(df, "start_time", "duration_min", "Duration", "min", "#4CAF50"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart(df, "start_time", "calories", "Calories", "kcal", "#FF9800"), use_container_width=True)

with tab4:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart(df, "start_time", "cadence", "Cadence", "spm", "#607D8B"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart(df, "start_time", "elevation_gain", "Elevation Gain", "m", "#795548"), use_container_width=True)
