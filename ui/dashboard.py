"""Streamlit dashboard for Garmin running activities — Multi-theme Edition."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.db import load_dataframe
from src.stats import weekly_summary, monthly_summary, personal_records

st.set_page_config(page_title="Garmin Running", page_icon="\u25c6", layout="wide")

# ── Preload all fonts ─────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500&family=Josefin+Sans:wght@300;400;600&family=Michroma&family=Outfit:wght@300;400;500&family=Orbitron:wght@400;500;600;700&family=Poiret+One&family=Rajdhani:wght@300;400;500;600&family=Sora:wght@300;400;500;600&display=swap');
</style>""", unsafe_allow_html=True)

# ── Theme (read from session state, selectbox is at bottom of page) ──
if "theme" not in st.session_state:
    st.session_state.theme = "Art Deco"
theme = st.session_state.theme

# ── Theme Configuration ───────────────────────────────
if theme == "Art Deco":
    PRIMARY, SECONDARY = "#00c9a7", "#c9a84c"
    TXT, DIM, MUTED = "#e8e0d0", "#a09880", "#605848"
    SURFACE, BG, BORDER = "#12121e", "#0a0a0f", "#1e1e2a"
    PLOT_BG = "rgba(18,18,30,0.25)"
    GRID = "rgba(30,30,42,0.4)"
    FONT_H, FONT_B = "Josefin Sans, sans-serif", "Jost, sans-serif"
    MARKER = "diamond"
    CC = {
        "dist": "#00c9a7", "pace": "#c9a84c", "hr1": "#c25a6e", "hr2": "#e05577",
        "dur": "#4ecdc4", "cal": "#8b7355", "cad": "#5a8c72", "elev": "#8b7355",
    }
elif theme == "Tokyo Neo":
    PRIMARY, SECONDARY = "#00f0ff", "#ff2d78"
    TXT, DIM, MUTED = "#e6edf3", "#8b949e", "#484f58"
    SURFACE, BG, BORDER = "#161b22", "#0d1117", "#21262d"
    PLOT_BG = "rgba(22,27,34,0.25)"
    GRID = "rgba(33,38,45,0.4)"
    FONT_H, FONT_B = "Sora, sans-serif", "Outfit, sans-serif"
    MARKER = "circle"
    CC = {
        "dist": "#00f0ff", "pace": "#ff2d78", "hr1": "#7c3aed", "hr2": "#a855f7",
        "dur": "#00ff88", "cal": "#ffb800", "cad": "#06b6d4", "elev": "#f97316",
    }
else:  # Blade Runner 2049
    PRIMARY, SECONDARY = "#e0943a", "#4a8fa5"
    TXT, DIM, MUTED = "#d8c9a3", "#8a7d68", "#554f44"
    SURFACE, BG, BORDER = "#191714", "#0f0e0c", "#2c2722"
    PLOT_BG = "rgba(25,23,20,0.25)"
    GRID = "rgba(44,39,34,0.4)"
    FONT_H, FONT_B = "Orbitron, sans-serif", "Rajdhani, sans-serif"
    MARKER = "x"
    CC = {
        "dist": "#e0943a", "pace": "#4a8fa5", "hr1": "#c45c3e", "hr2": "#d47a5a",
        "dur": "#6b9fa8", "cal": "#b87333", "cad": "#5a8fa0", "elev": "#8b6b4a",
    }

RADIUS = {"Art Deco": "0", "Tokyo Neo": "8px", "Blade Runner 2049": "2px"}[theme]

# ╔══════════════════════════════════════════════════════╗
# ║                  ART DECO CSS                        ║
# ╚══════════════════════════════════════════════════════╝

ART_DECO_CSS = """
/* ═══ GLOBAL ═══ */
.stApp {
    background: linear-gradient(180deg, #0a0a0f 0%, #08080d 50%, #0a0a12 100%);
    font-family: 'Jost', sans-serif;
}
section[data-testid="stSidebar"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1200px; padding-top: 0.5rem; }

h1, h2, h3 {
    font-family: 'Josefin Sans', sans-serif !important;
    font-weight: 300 !important; letter-spacing: 2px !important; color: #e8e0d0 !important;
}

/* ═══ METRICS ═══ */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #12121e 0%, #16162a 100%);
    border: 1px solid #1e1e2a; border-top: 2px solid #00c9a7;
    padding: 1rem 0.8rem; border-radius: 0;
    transition: all 0.35s ease;
}
[data-testid="stMetric"]:hover {
    border-color: #c9a84c40;
    border-top-color: #00c9a7;
    box-shadow: 0 0 20px rgba(201, 168, 76, 0.08), 0 2px 12px rgba(0, 0, 0, 0.3);
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    font-family: 'Josefin Sans', sans-serif !important; font-weight: 300 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-size: 0.7rem !important; color: #c9a84c !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Jost', sans-serif !important; font-weight: 400 !important;
    color: #00c9a7 !important; font-size: 1.4rem !important;
}
[data-testid="stMetricDelta"] { font-family: 'Jost', sans-serif !important; font-size: 0.8rem !important; }

/* ═══ TABS ═══ */
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #c9a84c40; background: transparent; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Josefin Sans', sans-serif !important; font-weight: 300 !important;
    letter-spacing: 3px !important; text-transform: uppercase !important;
    font-size: 0.78rem !important; color: #605848 !important;
    padding: 0.8rem 1.5rem !important; background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #a09880 !important; }
.stTabs [aria-selected="true"] { color: #00c9a7 !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #00c9a7 !important; }
.stTabs [data-baseweb="tab-border"] { background-color: #c9a84c40 !important; }

/* ═══ SELECTBOX (Theme Picker) ═══ */
[data-baseweb="select"] > div {
    background: #12121e !important; border: 1px solid #1e1e2a !important;
    border-radius: 0 !important; color: #c9a84c !important;
    font-family: 'Josefin Sans', sans-serif !important; font-size: 0.75rem !important;
    letter-spacing: 1px !important; text-align: center !important;
    display: flex !important; justify-content: center !important; align-items: center !important;
}
/* Center the currently selected value inside the visible select control */
[data-baseweb="select"] [role="combobox"] {
    display: flex !important; justify-content: center !important; align-items: center !important;
}
[data-baseweb="select"] [role="combobox"] span {
    width: 100% !important; text-align: center !important; display: block !important;
}
[data-baseweb="select"] [role="combobox"] input {
    text-align: center !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important;
}
[data-baseweb="select"], [data-baseweb="select"] * { text-align: center !important; justify-content: center !important; }
[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child [data-baseweb="select"],
[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child [data-baseweb="select"] * { text-align: left !important; justify-content: flex-start !important; }
[data-baseweb="select"] > div:hover { border-color: #c9a84c60 !important; }
[data-baseweb="select"] [data-baseweb="icon"] { display: none !important; }
[data-baseweb="popover"] [role="listbox"] { background: #12121e !important; border: 1px solid #1e1e2a !important; border-radius: 0 !important; }
[data-baseweb="popover"] [role="option"] {
    font-family: 'Josefin Sans', sans-serif !important; font-size: 0.75rem !important;
    color: #a09880 !important; letter-spacing: 1px !important; background: #12121e !important;
    text-align: center !important;
}
[data-baseweb="popover"] [role="option"]:hover { background: #1e1e2a !important; color: #e8e0d0 !important; }
[data-baseweb="popover"] [role="option"][aria-selected="true"] { color: #e8e0d0 !important; background: #1e1e2a !important; font-style: normal !important; font-weight: 600 !important; text-align: center !important; }

.stDateInput input {
    background-color: #12121e !important; border: 1px solid #1e1e2a !important;
    color: #e8e0d0 !important; border-radius: 0 !important;
}
hr { border-color: #c9a84c40 !important; }
[data-testid="stCaptionContainer"] {
    font-family: 'Jost', sans-serif !important; color: #605848 !important; letter-spacing: 1px !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #1e1e2a; }

/* ═══ ART DECO DECORATIONS ═══ */
.deco-header { text-align: center; padding: 1.5rem 0 0.5rem; }
.deco-ornament { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0.4rem 0; }
.deco-diamond { width: 8px; height: 8px; background: #00c9a7; transform: rotate(45deg); display: inline-block; }
.deco-diamond.gold { background: #c9a84c; }
.deco-diamond.lg { width: 10px; height: 10px; }
.deco-diamond.sm { width: 5px; height: 5px; opacity: 0.5; }
.deco-line { height: 1px; width: 100px; background: linear-gradient(to right, transparent, #c9a84c80, transparent); display: inline-block; }
.deco-title { font-family: 'Poiret One', cursive; font-size: 2.4rem; color: #e8e0d0; letter-spacing: 14px; margin: 0.2rem 0 0; text-transform: uppercase; }
.deco-subtitle { font-family: 'Josefin Sans', sans-serif; font-weight: 300; font-size: 0.7rem; color: #c9a84c; letter-spacing: 6px; text-transform: uppercase; margin-bottom: 0.2rem; }
.deco-meta { font-family: 'Jost', sans-serif; font-weight: 300; font-size: 0.7rem; color: #605848; letter-spacing: 2px; margin-top: 0.3rem; }

.deco-divider { display: flex; align-items: center; justify-content: center; margin: 1.2rem 0; gap: 10px; }
.deco-div-line { flex: 1; max-width: 160px; height: 1px; }
.deco-div-line.l { background: linear-gradient(to right, transparent, #c9a84c60); }
.deco-div-line.r { background: linear-gradient(to left, transparent, #c9a84c60); }

/* ═══ SHARED CARD STYLES (Art Deco) ═══ */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 0.8rem 0; }
.m-card {
    background: linear-gradient(145deg, #12121e 0%, #16162a 100%);
    border: 1px solid #1e1e2a; border-top: 2px solid #00c9a7;
    padding: 1rem 0.6rem; text-align: center; position: relative; overflow: hidden;
    transition: all 0.35s ease;
}
.m-card:hover {
    border-color: #c9a84c30;
    border-top-color: #00c9a7;
    box-shadow: 0 0 18px rgba(201, 168, 76, 0.08), 0 2px 12px rgba(0, 0, 0, 0.3);
    transform: translateY(-2px);
}
.m-card::after { content: ''; position: absolute; top: 2px; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, rgba(0,201,167,0.04) 0%, transparent 60%); pointer-events: none; transition: opacity 0.35s ease; }
.m-card:hover::after { background: linear-gradient(135deg, rgba(0,201,167,0.08) 0%, transparent 60%); }
.m-card .m-label { font-family: 'Josefin Sans', sans-serif; font-weight: 300; letter-spacing: 3px; font-size: 0.6rem; color: #c9a84c; text-transform: uppercase; margin-bottom: 0.4rem; }
.m-card .m-val { font-family: 'Jost', sans-serif; font-weight: 400; font-size: 1.4rem; color: #00c9a7; transition: color 0.35s ease; }
.m-card:hover .m-val { color: #00e5bf; }
.m-card .m-unit { font-family: 'Jost', sans-serif; font-weight: 300; font-size: 0.7rem; color: #605848; margin-left: 2px; }

.pr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; margin: 0.8rem 0; }
.pr-card {
    background: linear-gradient(145deg, #12121e, #18182c); border: 1px solid #1e1e2a;
    border-left: 3px solid #c9a84c; padding: 1rem; transition: all 0.35s ease;
}
.pr-card:hover {
    border-color: #c9a84c30;
    border-left-color: #c9a84c;
    box-shadow: -3px 0 15px rgba(201, 168, 76, 0.06), 0 2px 10px rgba(0, 0, 0, 0.25);
    transform: translateX(3px);
}
.pr-card .pr-label { font-family: 'Josefin Sans', sans-serif; font-weight: 300; letter-spacing: 2px; font-size: 0.6rem; color: #c9a84c; text-transform: uppercase; margin-bottom: 0.3rem; }
.pr-card .pr-val { font-family: 'Jost', sans-serif; font-weight: 500; font-size: 1.3rem; color: #00c9a7; transition: color 0.35s ease; }
.pr-card:hover .pr-val { color: #00e5bf; }
.pr-card .pr-detail { font-family: 'Jost', sans-serif; font-weight: 300; font-size: 0.72rem; color: #605848; margin-top: 0.2rem; }

.sec-label { font-family: 'Josefin Sans', sans-serif; font-weight: 300; letter-spacing: 3px; font-size: 0.8rem; color: #e8e0d0; text-transform: uppercase; display: flex; align-items: center; gap: 12px; margin: 1rem 0 0.5rem; }
.sec-label .sec-line { flex: 1; height: 1px; background: linear-gradient(to right, #c9a84c40, transparent); }
.latest-date { font-family: 'Josefin Sans', sans-serif; font-weight: 300; letter-spacing: 2px; font-size: 0.85rem; color: #a09880; text-transform: uppercase; margin-bottom: 0.3rem; }

@media (max-width: 768px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .pr-grid { grid-template-columns: 1fr; }
    .deco-title { font-size: 1.6rem; letter-spacing: 8px; }
}
"""

# ╔══════════════════════════════════════════════════════╗
# ║                  TOKYO NEO CSS                       ║
# ╚══════════════════════════════════════════════════════╝

TOKYO_NEO_CSS = """
/* ═══ GLOBAL ═══ */
.stApp {
    background: linear-gradient(135deg, #0d1117 0%, #0a0e1a 50%, #0d1117 100%);
    font-family: 'Outfit', sans-serif;
}
section[data-testid="stSidebar"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1200px; padding-top: 0.5rem; }

h1, h2, h3 {
    font-family: 'Sora', sans-serif !important;
    font-weight: 400 !important; letter-spacing: 1px !important; color: #e6edf3 !important;
}

/* ═══ METRICS ═══ */
[data-testid="stMetric"] {
    background: rgba(22, 27, 34, 0.9); border: 1px solid rgba(0, 240, 255, 0.1);
    border-top: 2px solid #00f0ff; padding: 1rem 0.8rem; border-radius: 8px;
    backdrop-filter: blur(8px); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
[data-testid="stMetric"]:hover {
    border-color: rgba(0, 240, 255, 0.35);
    box-shadow: 0 0 25px rgba(0, 240, 255, 0.12), 0 4px 15px rgba(0, 0, 0, 0.3);
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    font-family: 'Sora', sans-serif !important; font-weight: 300 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-size: 0.7rem !important; color: #8b949e !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important; font-weight: 500 !important;
    color: #00f0ff !important; font-size: 1.4rem !important;
    text-shadow: 0 0 8px rgba(0, 240, 255, 0.2);
}
[data-testid="stMetricDelta"] { font-family: 'Outfit', sans-serif !important; font-size: 0.8rem !important; }

/* ═══ TABS ═══ */
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #21262d; background: transparent; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Sora', sans-serif !important; font-weight: 300 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-size: 0.78rem !important; color: #484f58 !important;
    padding: 0.8rem 1.5rem !important; background: transparent !important;
    transition: color 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover { color: #8b949e !important; }
.stTabs [aria-selected="true"] { color: #00f0ff !important; text-shadow: 0 0 8px rgba(0, 240, 255, 0.3); }
.stTabs [data-baseweb="tab-highlight"] { background-color: #00f0ff !important; box-shadow: 0 0 10px rgba(0, 240, 255, 0.3); }
.stTabs [data-baseweb="tab-border"] { background-color: #21262d !important; }

/* ═══ SELECTBOX (Theme Picker) ═══ */
    [data-baseweb="select"] > div {
    background: rgba(22, 27, 34, 0.9) !important; border: 1px solid #21262d !important;
    border-radius: 8px !important; color: #00f0ff !important; backdrop-filter: blur(8px);
    font-family: 'Sora', sans-serif !important; font-size: 0.75rem !important;
    letter-spacing: 1px !important; text-align: center !important;
    display: flex !important; justify-content: center !important; align-items: center !important;
}
    /* Center the currently selected value inside the visible select control */
    [data-baseweb="select"] [role="combobox"] {
        display: flex !important; justify-content: center !important; align-items: center !important;
    }
    [data-baseweb="select"] [role="combobox"] span {
        width: 100% !important; text-align: center !important; display: block !important;
    }
    [data-baseweb="select"] [role="combobox"] input {
        text-align: center !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important;
    }
[data-baseweb="select"], [data-baseweb="select"] * { text-align: center !important; justify-content: center !important; }
[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child [data-baseweb="select"],
[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child [data-baseweb="select"] * { text-align: left !important; justify-content: flex-start !important; }
[data-baseweb="select"] > div:hover { border-color: rgba(0, 240, 255, 0.3) !important; }
[data-baseweb="select"] [data-baseweb="icon"] { display: none !important; }
[data-baseweb="popover"] [role="listbox"] { background: #161b22 !important; border: 1px solid #21262d !important; border-radius: 8px !important; }
    [data-baseweb="popover"] [role="option"] {
    font-family: 'Sora', sans-serif !important; font-size: 0.75rem !important;
    color: #8b949e !important; letter-spacing: 1px !important; background: #161b22 !important;
    text-align: center !important;
}
[data-baseweb="popover"] [role="option"]:hover { background: #21262d !important; color: #e6edf3 !important; }
    [data-baseweb="popover"] [role="option"][aria-selected="true"] { color: #00f0ff !important; background: #161b22 !important; font-style: normal !important; font-weight: 600 !important; text-align: center !important; }

.stDateInput input {
    background-color: #161b22 !important; border: 1px solid #21262d !important;
    color: #e6edf3 !important; border-radius: 6px !important;
}
hr { border-color: #21262d !important; }
[data-testid="stCaptionContainer"] {
    font-family: 'Outfit', sans-serif !important; color: #484f58 !important; letter-spacing: 1px !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #21262d; border-radius: 3px; }

/* ═══ NEO HEADER ═══ */
.neo-header { text-align: center; padding: 1.5rem 0 0.5rem; }
.neo-header-line {
    height: 2px; max-width: 400px; margin: 0 auto; border-radius: 1px;
    background: linear-gradient(90deg, transparent, #00f0ff, #ff2d78, #7c3aed, #00f0ff, transparent);
    background-size: 200% auto; animation: neo-flow 4s linear infinite;
}
@keyframes neo-flow { 0% { background-position: 0% center; } 100% { background-position: 200% center; } }

.neo-dots { display: flex; justify-content: center; gap: 10px; margin: 0.5rem 0; }
.neo-dot {
    width: 6px; height: 6px; background: #ff2d78; border-radius: 50%;
    box-shadow: 0 0 8px rgba(255, 45, 120, 0.5); animation: neo-pulse 2s ease-in-out infinite;
}
@keyframes neo-pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }

.neo-title { font-family: 'Michroma', sans-serif; font-size: 1.8rem; color: #e6edf3; letter-spacing: 8px; margin: 0.3rem 0; text-transform: uppercase; }
.neo-accent { color: #00f0ff; text-shadow: 0 0 20px rgba(0, 240, 255, 0.3); }
.neo-subtitle { font-family: 'Sora', sans-serif; font-weight: 300; font-size: 0.65rem; color: #484f58; letter-spacing: 4px; text-transform: uppercase; }
.neo-meta { font-family: 'Outfit', sans-serif; font-weight: 300; font-size: 0.7rem; color: #484f58; letter-spacing: 2px; margin-top: 0.3rem; }

/* ═══ NEO DIVIDER ═══ */
.neo-divider { display: flex; align-items: center; justify-content: center; margin: 1.2rem 0; gap: 12px; }
.neo-div-line { flex: 1; max-width: 120px; height: 1px; }
.neo-div-line.l { background: linear-gradient(to right, transparent, #00f0ff40); }
.neo-div-line.r { background: linear-gradient(to left, transparent, #00f0ff40); }

/* ═══ METRIC GRID (Neo) ═══ */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 0.8rem 0; }
.m-card {
    background: rgba(22, 27, 34, 0.9); border: 1px solid rgba(0, 240, 255, 0.1);
    border-top: 2px solid #00f0ff; padding: 1rem 0.6rem; text-align: center;
    border-radius: 8px; backdrop-filter: blur(8px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative; overflow: hidden;
}
.m-card::after { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, rgba(0,240,255,0.04) 0%, transparent 60%); pointer-events: none; }
.m-card:hover {
    border-color: rgba(0, 240, 255, 0.4);
    box-shadow: 0 0 25px rgba(0, 240, 255, 0.15), 0 4px 20px rgba(0, 0, 0, 0.3);
    transform: translateY(-3px);
}
.m-card .m-label { font-family: 'Sora', sans-serif; font-weight: 300; letter-spacing: 2px; font-size: 0.6rem; color: #8b949e; text-transform: uppercase; margin-bottom: 0.4rem; }
.m-card .m-val { font-family: 'Outfit', sans-serif; font-weight: 500; font-size: 1.4rem; color: #00f0ff; text-shadow: 0 0 10px rgba(0, 240, 255, 0.3); transition: text-shadow 0.3s ease; }
.m-card:hover .m-val { text-shadow: 0 0 20px rgba(0, 240, 255, 0.5); }
.m-card .m-unit { font-family: 'Outfit', sans-serif; font-weight: 300; font-size: 0.7rem; color: #484f58; margin-left: 2px; }

/* ═══ PR CARDS (Neo) ═══ */
.pr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; margin: 0.8rem 0; }
.pr-card {
    background: rgba(22, 27, 34, 0.9); border: 1px solid rgba(255, 45, 120, 0.1);
    border-left: 3px solid #ff2d78; padding: 1rem; border-radius: 8px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.pr-card:hover {
    border-color: rgba(255, 45, 120, 0.4);
    box-shadow: -4px 0 20px rgba(255, 45, 120, 0.1), 0 4px 15px rgba(0, 0, 0, 0.2);
    transform: translateX(4px);
}
.pr-card .pr-label { font-family: 'Sora', sans-serif; font-weight: 300; letter-spacing: 2px; font-size: 0.6rem; color: #8b949e; text-transform: uppercase; margin-bottom: 0.3rem; }
.pr-card .pr-val { font-family: 'Outfit', sans-serif; font-weight: 500; font-size: 1.3rem; color: #ff2d78; text-shadow: 0 0 8px rgba(255, 45, 120, 0.2); }
.pr-card .pr-detail { font-family: 'Outfit', sans-serif; font-weight: 300; font-size: 0.72rem; color: #484f58; margin-top: 0.2rem; }

/* ═══ SECTION LABEL (Neo) ═══ */
.sec-label { font-family: 'Sora', sans-serif; font-weight: 300; letter-spacing: 3px; font-size: 0.8rem; color: #e6edf3; text-transform: uppercase; display: flex; align-items: center; gap: 12px; margin: 1rem 0 0.5rem; }
.sec-label .sec-line { flex: 1; height: 1px; background: linear-gradient(to right, #21262d, transparent); }
.latest-date { font-family: 'Sora', sans-serif; font-weight: 300; letter-spacing: 2px; font-size: 0.85rem; color: #8b949e; text-transform: uppercase; margin-bottom: 0.3rem; }

/* ═══ VISUAL BOARD ═══ */
.neo-board {
    margin: 1rem 0; padding: 1.2rem; background: rgba(22, 27, 34, 0.6);
    border: 1px solid #21262d; border-radius: 10px; backdrop-filter: blur(4px);
}
.neo-board-title {
    font-family: 'Sora', sans-serif; font-weight: 300; font-size: 0.6rem;
    color: #484f58; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 0.8rem;
}
.board-row { display: flex; align-items: center; margin: 0.7rem 0; gap: 12px; }
.board-label { width: 75px; font-family: 'Sora', sans-serif; font-weight: 300; font-size: 0.65rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; flex-shrink: 0; }
.board-bar-wrap { flex: 1; height: 22px; background: #161b22; border-radius: 6px; position: relative; overflow: visible; }
.board-bar {
    height: 100%; border-radius: 6px; transform-origin: left;
    animation: bar-grow 1.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    position: relative;
}
.board-bar.cyan { background: linear-gradient(90deg, #00f0ff, rgba(0, 240, 255, 0.6)); box-shadow: 0 0 12px rgba(0, 240, 255, 0.15); }
.board-bar.green { background: linear-gradient(90deg, #00ff88, rgba(0, 255, 136, 0.6)); box-shadow: 0 0 12px rgba(0, 255, 136, 0.15); }
.board-bar.pink { background: linear-gradient(90deg, #ff2d78, rgba(255, 45, 120, 0.6)); box-shadow: 0 0 12px rgba(255, 45, 120, 0.15); }
.board-bar.amber { background: linear-gradient(90deg, #ffb800, rgba(255, 184, 0, 0.6)); box-shadow: 0 0 12px rgba(255, 184, 0, 0.15); }
@keyframes bar-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

.board-avg {
    position: absolute; top: -4px; width: 2px; height: calc(100% + 8px);
    background: #ff2d78; box-shadow: 0 0 8px rgba(255, 45, 120, 0.5); z-index: 2;
}
.board-avg span {
    position: absolute; top: -15px; left: 50%; transform: translateX(-50%);
    font-family: 'Sora', sans-serif; font-size: 0.45rem; font-weight: 400;
    color: #ff2d78; letter-spacing: 1px;
}
.board-val { width: 80px; text-align: right; font-family: 'Outfit', sans-serif; font-weight: 500; font-size: 0.95rem; color: #00f0ff; flex-shrink: 0; }
.board-unit { font-weight: 300; font-size: 0.65rem; color: #484f58; margin-left: 2px; }

@media (max-width: 768px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .pr-grid { grid-template-columns: 1fr; }
    .neo-title { font-size: 1.3rem; letter-spacing: 4px; }
}
"""

# ╔══════════════════════════════════════════════════════╗
# ║               BLADE RUNNER 2049 CSS                  ║
# ╚══════════════════════════════════════════════════════╝

BLADE_RUNNER_CSS = """
/* ═══ GLOBAL ═══ */
.stApp {
    background: linear-gradient(160deg, #0f0e0c 0%, #131110 40%, #110f0d 70%, #0f0e0c 100%);
    font-family: 'Rajdhani', sans-serif;
}
section[data-testid="stSidebar"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1200px; padding-top: 0.5rem; }

h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 400 !important; letter-spacing: 3px !important; color: #d8c9a3 !important;
}

/* ═══ METRICS ═══ */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #191714 0%, #1d1a16 100%);
    border: 1px solid #2c2722; border-top: 2px solid #e0943a;
    padding: 1rem 0.8rem; border-radius: 2px;
    transition: all 0.4s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(224, 148, 58, 0.2);
    border-top-color: #e0943a;
    box-shadow: 0 0 25px rgba(224, 148, 58, 0.08), 0 4px 15px rgba(0, 0, 0, 0.4);
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    font-family: 'Orbitron', sans-serif !important; font-weight: 400 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-size: 0.65rem !important; color: #8a7d68 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Rajdhani', sans-serif !important; font-weight: 500 !important;
    color: #e0943a !important; font-size: 1.4rem !important;
    text-shadow: 0 0 12px rgba(224, 148, 58, 0.15);
}
[data-testid="stMetricDelta"] { font-family: 'Rajdhani', sans-serif !important; font-size: 0.8rem !important; }

/* ═══ TABS ═══ */
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #2c2722; background: transparent; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Orbitron', sans-serif !important; font-weight: 400 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    font-size: 0.72rem !important; color: #554f44 !important;
    padding: 0.8rem 1.5rem !important; background: transparent !important;
    transition: color 0.3s ease;
}
.stTabs [data-baseweb="tab"]:hover { color: #8a7d68 !important; }
.stTabs [aria-selected="true"] { color: #e0943a !important; text-shadow: 0 0 10px rgba(224, 148, 58, 0.2); }
.stTabs [data-baseweb="tab-highlight"] { background-color: #e0943a !important; box-shadow: 0 0 8px rgba(224, 148, 58, 0.2); }
.stTabs [data-baseweb="tab-border"] { background-color: #2c2722 !important; }

/* ═══ SELECTBOX (Theme Picker) ═══ */
    [data-baseweb="select"] > div {
    background: #191714 !important; border: 1px solid #2c2722 !important;
    border-radius: 2px !important; color: #e0943a !important;
    font-family: 'Orbitron', sans-serif !important; font-size: 0.7rem !important;
    letter-spacing: 1px !important; text-align: center !important;
    display: flex !important; justify-content: center !important; align-items: center !important;
}
    /* Center the currently selected value inside the visible select control */
    [data-baseweb="select"] [role="combobox"] {
        display: flex !important; justify-content: center !important; align-items: center !important;
    }
    [data-baseweb="select"] [role="combobox"] span {
        width: 100% !important; text-align: center !important; display: block !important;
    }
    [data-baseweb="select"] [role="combobox"] input {
        text-align: center !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important;
    }
[data-baseweb="select"], [data-baseweb="select"] * { text-align: center !important; justify-content: center !important; }
[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child [data-baseweb="select"],
[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child [data-baseweb="select"] * { text-align: left !important; justify-content: flex-start !important; }
[data-baseweb="select"] > div:hover { border-color: rgba(224, 148, 58, 0.3) !important; }
[data-baseweb="select"] [data-baseweb="icon"] { display: none !important; }
[data-baseweb="popover"] [role="listbox"] { background: #191714 !important; border: 1px solid #2c2722 !important; border-radius: 2px !important; }
    [data-baseweb="popover"] [role="option"] {
    font-family: 'Orbitron', sans-serif !important; font-size: 0.7rem !important;
    color: #8a7d68 !important; letter-spacing: 1px !important; background: #191714 !important;
    text-align: center !important;
}
[data-baseweb="popover"] [role="option"]:hover { background: #2c2722 !important; color: #d8c9a3 !important; }
    [data-baseweb="popover"] [role="option"][aria-selected="true"] { color: #e0943a !important; background: #191714 !important; font-style: normal !important; font-weight: 600 !important; text-align: center !important; }

.stDateInput input {
    background-color: #191714 !important; border: 1px solid #2c2722 !important;
    color: #d8c9a3 !important; border-radius: 2px !important;
}
hr { border-color: #2c272240 !important; }
[data-testid="stCaptionContainer"] {
    font-family: 'Rajdhani', sans-serif !important; color: #554f44 !important; letter-spacing: 1px !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f0e0c; }
::-webkit-scrollbar-thumb { background: #2c2722; border-radius: 1px; }

/* ═══ BLADE RUNNER HEADER ═══ */
.br-header { text-align: center; padding: 1.5rem 0 0.5rem; position: relative; }
.br-scanline {
    height: 1px; max-width: 350px; margin: 0 auto;
    background: linear-gradient(90deg, transparent, #e0943a60, #e0943a, #e0943a60, transparent);
}
.br-scanline.dim { opacity: 0.3; max-width: 250px; margin-top: 3px; }
.br-title {
    font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 2rem;
    color: #e0943a; letter-spacing: 12px; margin: 0.6rem 0 0.1rem;
    text-transform: uppercase;
    text-shadow: 0 0 30px rgba(224, 148, 58, 0.2), 0 0 60px rgba(224, 148, 58, 0.05);
}
.br-title .br-accent { color: #4a8fa5; text-shadow: 0 0 20px rgba(74, 143, 165, 0.2); }
.br-subtitle {
    font-family: 'Orbitron', sans-serif; font-weight: 400; font-size: 0.6rem;
    color: #554f44; letter-spacing: 6px; text-transform: uppercase;
}
.br-subtitle .br-bracket { color: #8a7d68; }
.br-meta {
    font-family: 'Rajdhani', sans-serif; font-weight: 400; font-size: 0.75rem;
    color: #554f44; letter-spacing: 2px; margin-top: 0.4rem;
}

/* ═══ BLADE RUNNER DIVIDER ═══ */
.br-divider { display: flex; align-items: center; justify-content: center; margin: 1.2rem 0; gap: 12px; }
.br-div-line { flex: 1; max-width: 140px; height: 1px; }
.br-div-line.l { background: linear-gradient(to right, transparent, #e0943a40); }
.br-div-line.r { background: linear-gradient(to left, transparent, #e0943a40); }
.br-div-dot { width: 4px; height: 4px; background: #e0943a; opacity: 0.6; }

/* ═══ METRIC GRID (BR) ═══ */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 0.8rem 0; }
.m-card {
    background: linear-gradient(145deg, #191714 0%, #1d1a16 100%);
    border: 1px solid #2c2722; border-top: 2px solid #e0943a;
    padding: 1rem 0.6rem; text-align: center; border-radius: 2px;
    transition: all 0.4s ease; position: relative; overflow: hidden;
}
.m-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 3px,
        rgba(224, 148, 58, 0.008) 3px, rgba(224, 148, 58, 0.008) 4px
    );
    pointer-events: none;
}
.m-card::after {
    content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: linear-gradient(135deg, rgba(224, 148, 58, 0.03) 0%, transparent 60%);
    pointer-events: none; transition: opacity 0.4s ease;
}
.m-card:hover {
    border-color: rgba(224, 148, 58, 0.25);
    border-top-color: #e0943a;
    box-shadow: 0 0 25px rgba(224, 148, 58, 0.06), 0 4px 20px rgba(0, 0, 0, 0.4);
    transform: translateY(-2px);
}
.m-card:hover::after { background: linear-gradient(135deg, rgba(224, 148, 58, 0.06) 0%, transparent 60%); }
.m-card .m-label {
    font-family: 'Orbitron', sans-serif; font-weight: 400; letter-spacing: 2px;
    font-size: 0.55rem; color: #8a7d68; text-transform: uppercase; margin-bottom: 0.4rem;
}
.m-card .m-val {
    font-family: 'Rajdhani', sans-serif; font-weight: 500; font-size: 1.4rem;
    color: #e0943a; text-shadow: 0 0 10px rgba(224, 148, 58, 0.15);
    transition: text-shadow 0.4s ease;
}
.m-card:hover .m-val { text-shadow: 0 0 20px rgba(224, 148, 58, 0.3); }
.m-card .m-unit { font-family: 'Rajdhani', sans-serif; font-weight: 300; font-size: 0.7rem; color: #554f44; margin-left: 2px; }

/* ═══ PR CARDS (BR) ═══ */
.pr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; margin: 0.8rem 0; }
.pr-card {
    background: linear-gradient(145deg, #191714, #1d1a16); border: 1px solid #2c2722;
    border-left: 3px solid #4a8fa5; padding: 1rem; border-radius: 2px;
    transition: all 0.4s ease; position: relative; overflow: hidden;
}
.pr-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 3px,
        rgba(74, 143, 165, 0.008) 3px, rgba(74, 143, 165, 0.008) 4px
    );
    pointer-events: none;
}
.pr-card:hover {
    border-color: rgba(74, 143, 165, 0.25);
    border-left-color: #4a8fa5;
    box-shadow: -3px 0 20px rgba(74, 143, 165, 0.06), 0 4px 15px rgba(0, 0, 0, 0.3);
    transform: translateX(3px);
}
.pr-card .pr-label {
    font-family: 'Orbitron', sans-serif; font-weight: 400; letter-spacing: 2px;
    font-size: 0.55rem; color: #8a7d68; text-transform: uppercase; margin-bottom: 0.3rem;
}
.pr-card .pr-val {
    font-family: 'Rajdhani', sans-serif; font-weight: 600; font-size: 1.3rem;
    color: #4a8fa5; text-shadow: 0 0 8px rgba(74, 143, 165, 0.15);
}
.pr-card .pr-detail { font-family: 'Rajdhani', sans-serif; font-weight: 300; font-size: 0.72rem; color: #554f44; margin-top: 0.2rem; }

/* ═══ SECTION LABEL (BR) ═══ */
.sec-label {
    font-family: 'Orbitron', sans-serif; font-weight: 400; letter-spacing: 3px;
    font-size: 0.75rem; color: #d8c9a3; text-transform: uppercase;
    display: flex; align-items: center; gap: 12px; margin: 1rem 0 0.5rem;
}
.sec-label .sec-line { flex: 1; height: 1px; background: linear-gradient(to right, #2c272280, transparent); }
.latest-date {
    font-family: 'Orbitron', sans-serif; font-weight: 400; letter-spacing: 3px;
    font-size: 0.75rem; color: #8a7d68; text-transform: uppercase; margin-bottom: 0.3rem;
}

/* ═══ VISUAL BOARD (BR) ═══ */
.br-board {
    margin: 1rem 0; padding: 1.2rem; position: relative; overflow: hidden;
    background: linear-gradient(145deg, #191714 0%, #1a1815 100%);
    border: 1px solid #2c2722; border-radius: 2px;
}
.br-board::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 2px,
        rgba(224, 148, 58, 0.01) 2px, rgba(224, 148, 58, 0.01) 4px
    );
    pointer-events: none;
}
.br-board-title {
    font-family: 'Orbitron', sans-serif; font-weight: 400; font-size: 0.55rem;
    color: #554f44; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 0.8rem;
}
.br-board .board-row { display: flex; align-items: center; margin: 0.7rem 0; gap: 12px; }
.br-board .board-label {
    width: 75px; font-family: 'Orbitron', sans-serif; font-weight: 400;
    font-size: 0.55rem; color: #8a7d68; text-transform: uppercase; letter-spacing: 1px; flex-shrink: 0;
}
.br-board .board-bar-wrap { flex: 1; height: 20px; background: #131110; border-radius: 1px; position: relative; overflow: visible; }
.br-board .board-bar {
    height: 100%; border-radius: 1px; transform-origin: left;
    animation: br-bar-grow 1.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
    position: relative;
}
.br-board .board-bar.amber { background: linear-gradient(90deg, #e0943a, rgba(224, 148, 58, 0.5)); box-shadow: 0 0 10px rgba(224, 148, 58, 0.1); }
.br-board .board-bar.steel { background: linear-gradient(90deg, #4a8fa5, rgba(74, 143, 165, 0.5)); box-shadow: 0 0 10px rgba(74, 143, 165, 0.1); }
.br-board .board-bar.copper { background: linear-gradient(90deg, #b87333, rgba(184, 115, 51, 0.5)); box-shadow: 0 0 10px rgba(184, 115, 51, 0.1); }
.br-board .board-bar.terra { background: linear-gradient(90deg, #c45c3e, rgba(196, 92, 62, 0.5)); box-shadow: 0 0 10px rgba(196, 92, 62, 0.1); }
@keyframes br-bar-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

.br-board .board-avg {
    position: absolute; top: -4px; width: 2px; height: calc(100% + 8px);
    background: #4a8fa5; box-shadow: 0 0 6px rgba(74, 143, 165, 0.4); z-index: 2;
}
.br-board .board-avg span {
    position: absolute; top: -15px; left: 50%; transform: translateX(-50%);
    font-family: 'Orbitron', sans-serif; font-size: 0.4rem; font-weight: 400;
    color: #4a8fa5; letter-spacing: 2px;
}
.br-board .board-val {
    width: 80px; text-align: right; font-family: 'Rajdhani', sans-serif;
    font-weight: 500; font-size: 0.95rem; color: #e0943a; flex-shrink: 0;
}
.br-board .board-unit { font-weight: 300; font-size: 0.65rem; color: #554f44; margin-left: 2px; }

@media (max-width: 768px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .pr-grid { grid-template-columns: 1fr; }
    .br-title { font-size: 1.4rem; letter-spacing: 6px; }
}
"""

# ── Inject Theme CSS ──────────────────────────────────
_theme_css = {"Art Deco": ART_DECO_CSS, "Tokyo Neo": TOKYO_NEO_CSS, "Blade Runner 2049": BLADE_RUNNER_CSS}
st.markdown(f"<style>{_theme_css[theme]}</style>", unsafe_allow_html=True)

# ── Pace Zone Constants ──────────────────────────────
ZONE_BINS = [0, 3.333, 4.0, 4.583, 5.417, float("inf")]
ZONE_LABELS = ["Speed", "Threshold", "Tempo", "Easy", "Recovery"]
ZONE_COLORS = ["#e53935", "#ff9800", "#fdd835", "#42a5f5", "#ab47bc"]

# ── Helpers ───────────────────────────────────────────

def divider():
    if theme == "Art Deco":
        st.markdown("""<div class="deco-divider">
            <div class="deco-div-line l"></div><span class="deco-diamond sm"></span>
            <span class="deco-diamond gold lg"></span><span class="deco-diamond sm"></span>
            <div class="deco-div-line r"></div></div>""", unsafe_allow_html=True)
    elif theme == "Tokyo Neo":
        st.markdown("""<div class="neo-divider">
            <div class="neo-div-line l"></div>
            <span class="neo-dot" style="width:4px;height:4px;animation-duration:3s;"></span>
            <span class="neo-dot" style="width:5px;height:5px;"></span>
            <span class="neo-dot" style="width:4px;height:4px;animation-duration:3s;animation-delay:0.5s;"></span>
            <div class="neo-div-line r"></div></div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="br-divider">
            <div class="br-div-line l"></div>
            <div class="br-div-dot"></div>
            <div class="br-div-line r"></div></div>""", unsafe_allow_html=True)


def section_label(text):
    if theme == "Art Deco":
        st.markdown(f'<div class="sec-label"><span class="deco-diamond sm gold"></span>'
                    f'{text}<div class="sec-line"></div></div>', unsafe_allow_html=True)
    elif theme == "Tokyo Neo":
        st.markdown(f'<div class="sec-label"><span style="width:4px;height:4px;background:#ff2d78;'
                    f'border-radius:50%;display:inline-block;box-shadow:0 0 6px rgba(255,45,120,0.4);"></span>'
                    f'{text}<div class="sec-line"></div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="sec-label"><span style="width:4px;height:4px;background:#e0943a;'
                    f'display:inline-block;box-shadow:0 0 6px rgba(224,148,58,0.3);"></span>'
                    f'{text}<div class="sec-line"></div></div>', unsafe_allow_html=True)


def _layout(title, unit):
    return dict(
        title=dict(text=title.upper(), font=dict(family=FONT_H, size=13, color=TXT), x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG,
        font=dict(family=FONT_B, color=DIM, size=11),
        xaxis=dict(gridcolor=GRID, linecolor=BORDER, tickfont=dict(color=MUTED, size=10), title=None),
        yaxis=dict(title=dict(text=unit, font=dict(size=11, color=DIM)),
                   gridcolor=GRID, linecolor=BORDER, tickfont=dict(color=MUTED, size=10)),
        height=350, margin=dict(l=50, r=20, t=50, b=30), hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=PRIMARY,
                        font=dict(color=TXT, family=FONT_B, size=12)),
    )


def make_chart(df, x, y, title, unit, color):
    data = df.dropna(subset=[y])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data[x], y=data[y], mode="lines+markers",
        marker=dict(size=5, color=color, symbol=MARKER, line=dict(width=1, color=BG)),
        line=dict(color=color, width=2),
        hovertemplate=f"%{{x|%b %d, %Y}}<br><b>%{{y:.1f}} {unit}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(title, unit))
    return fig


def make_dual_chart(df, x, y1, y2, title, label1, label2, unit, c1, c2):
    data = df.dropna(subset=[y1, y2])
    fig = go.Figure()
    for y, label, color in [(y1, label1, c1), (y2, label2, c2)]:
        fig.add_trace(go.Scatter(
            x=data[x], y=data[y], name=label, mode="lines+markers",
            marker=dict(size=5, color=color, symbol=MARKER, line=dict(width=1, color=BG)),
            line=dict(color=color, width=2),
            hovertemplate=f"%{{x|%b %d, %Y}}<br><b>{label}: %{{y:.0f}} {unit}</b><extra></extra>",
        ))
    layout = _layout(title, unit)
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=1.02,
                            font=dict(color=DIM, family=FONT_H, size=11))
    fig.update_layout(**layout)
    return fig


def neo_visual_board(latest, df):
    """Animated bar chart comparing latest run to averages (Tokyo Neo only)."""
    bars = []
    colors = ["cyan", "pink", "green", "amber"]

    # Distance
    max_d = df["distance_km"].max()
    avg_d = df["distance_km"].mean()
    if max_d > 0:
        bars.append(("Distance", f"{latest['distance_km']:.1f}", "km",
                      latest["distance_km"] / max_d * 100, avg_d / max_d * 100, colors[0]))

    # Pace (inverted — longer bar = faster)
    min_p, max_p = df["pace_min_km"].min(), df["pace_min_km"].max()
    rng = max_p - min_p if max_p > min_p else 1
    avg_p = df["pace_min_km"].mean()
    pm, ps = int(latest["pace_min_km"]), int((latest["pace_min_km"] % 1) * 60)
    bars.append(("Pace", f"{pm}:{ps:02d}", "/km",
                  max((max_p - latest["pace_min_km"]) / rng * 100, 3),
                  max((max_p - avg_p) / rng * 100, 3), colors[1]))

    # Duration
    max_dur = df["duration_min"].max()
    avg_dur = df["duration_min"].mean()
    if max_dur > 0:
        bars.append(("Duration", f"{int(latest['duration_min'])}", "min",
                      latest["duration_min"] / max_dur * 100, avg_dur / max_dur * 100, colors[2]))

    # Cadence
    if pd.notna(latest["cadence"]):
        max_c = df["cadence"].dropna().max()
        avg_c = df["cadence"].dropna().mean()
        if max_c > 0:
            bars.append(("Cadence", f"{latest['cadence']:.0f}", "spm",
                          latest["cadence"] / max_c * 100, avg_c / max_c * 100, colors[3]))

    html = '<div class="neo-board"><div class="neo-board-title">Latest vs Your Range</div>'
    for label, val, unit, pct, avg_pct, clr in bars:
        html += f'''<div class="board-row">
            <div class="board-label">{label}</div>
            <div class="board-bar-wrap">
                <div class="board-bar {clr}" style="width: {pct}%;"></div>
                <div class="board-avg" style="left: {avg_pct}%;"><span>AVG</span></div>
            </div>
            <div class="board-val">{val}<span class="board-unit">{unit}</span></div>
        </div>'''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def br_visual_board(latest, df):
    """Animated bar chart — Blade Runner 2049 dusty/industrial style."""
    bars = []
    colors = ["amber", "steel", "copper", "terra"]

    max_d = df["distance_km"].max()
    avg_d = df["distance_km"].mean()
    if max_d > 0:
        bars.append(("Distance", f"{latest['distance_km']:.1f}", "km",
                      latest["distance_km"] / max_d * 100, avg_d / max_d * 100, colors[0]))

    min_p, max_p = df["pace_min_km"].min(), df["pace_min_km"].max()
    rng = max_p - min_p if max_p > min_p else 1
    avg_p = df["pace_min_km"].mean()
    pm, ps = int(latest["pace_min_km"]), int((latest["pace_min_km"] % 1) * 60)
    bars.append(("Pace", f"{pm}:{ps:02d}", "/km",
                  max((max_p - latest["pace_min_km"]) / rng * 100, 3),
                  max((max_p - avg_p) / rng * 100, 3), colors[1]))

    max_dur = df["duration_min"].max()
    avg_dur = df["duration_min"].mean()
    if max_dur > 0:
        bars.append(("Duration", f"{int(latest['duration_min'])}", "min",
                      latest["duration_min"] / max_dur * 100, avg_dur / max_dur * 100, colors[2]))

    if pd.notna(latest["cadence"]):
        max_c = df["cadence"].dropna().max()
        avg_c = df["cadence"].dropna().mean()
        if max_c > 0:
            bars.append(("Cadence", f"{latest['cadence']:.0f}", "spm",
                          latest["cadence"] / max_c * 100, avg_c / max_c * 100, colors[3]))

    html = '<div class="br-board"><div class="br-board-title">Latest // Run Data</div>'
    for label, val, unit, pct, avg_pct, clr in bars:
        html += f'''<div class="board-row">
            <div class="board-label">{label}</div>
            <div class="board-bar-wrap">
                <div class="board-bar {clr}" style="width: {pct}%;"></div>
                <div class="board-avg" style="left: {avg_pct}%;"><span>AVG</span></div>
            </div>
            <div class="board-val">{val}<span class="board-unit">{unit}</span></div>
        </div>'''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def deco_radar_chart(stats_a, stats_b, label_a, label_b):
    """Radar chart — Art Deco cyan/gold palette."""
    categories = ["Distance", "Runs", "Speed", "Cadence", "Elevation", "Calories"]

    def get_vals(s):
        pace = s["Avg Pace"]
        return [
            s["Total km"], s["Runs"],
            1 / pace if pd.notna(pace) and pace > 0 else 0,
            s.get("Avg Cadence", 0) or 0,
            s["Total Elevation"] or 0, s["Total Calories"] or 0,
        ]

    raw_a, raw_b = get_vals(stats_a), get_vals(stats_b)
    norm_a, norm_b = [], []
    for va, vb in zip(raw_a, raw_b):
        mx = max(abs(va), abs(vb))
        if mx > 0:
            norm_a.append(va / mx * 100)
            norm_b.append(vb / mx * 100)
        else:
            norm_a.append(50)
            norm_b.append(50)

    fig = go.Figure()
    for vals, name, color, fill in [
        (norm_a, label_a, "#00c9a7", "rgba(0,201,167,0.08)"),
        (norm_b, label_b, "#c9a84c", "rgba(201,168,76,0.08)"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill="toself", name=name,
            line=dict(color=color, width=2), fillcolor=fill,
            marker=dict(size=5),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 105], gridcolor="#1e1e2a",
                            linecolor="#1e1e2a", tickfont=dict(size=8, color="#605848")),
            angularaxis=dict(gridcolor="#1e1e2a", linecolor="#1e1e2a",
                             tickfont=dict(size=11, color="#a09880", family="Josefin Sans, sans-serif")),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Jost, sans-serif", color="#a09880"),
        legend=dict(font=dict(color="#a09880", family="Josefin Sans, sans-serif", size=11),
                    orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
        height=400, margin=dict(l=60, r=60, t=30, b=50),
    )
    return fig


def br_radar_chart(stats_a, stats_b, label_a, label_b):
    """Radar chart — Blade Runner 2049 amber/steel palette."""
    categories = ["Distance", "Runs", "Speed", "Cadence", "Elevation", "Calories"]

    def get_vals(s):
        pace = s["Avg Pace"]
        return [
            s["Total km"], s["Runs"],
            1 / pace if pd.notna(pace) and pace > 0 else 0,
            s.get("Avg Cadence", 0) or 0,
            s["Total Elevation"] or 0, s["Total Calories"] or 0,
        ]

    raw_a, raw_b = get_vals(stats_a), get_vals(stats_b)
    norm_a, norm_b = [], []
    for va, vb in zip(raw_a, raw_b):
        mx = max(abs(va), abs(vb))
        if mx > 0:
            norm_a.append(va / mx * 100)
            norm_b.append(vb / mx * 100)
        else:
            norm_a.append(50)
            norm_b.append(50)

    fig = go.Figure()
    for vals, name, color, fill in [
        (norm_a, label_a, "#e0943a", "rgba(224,148,58,0.08)"),
        (norm_b, label_b, "#4a8fa5", "rgba(74,143,165,0.08)"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill="toself", name=name,
            line=dict(color=color, width=2), fillcolor=fill,
            marker=dict(size=5),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 105], gridcolor="#2c2722",
                            linecolor="#2c2722", tickfont=dict(size=8, color="#554f44")),
            angularaxis=dict(gridcolor="#2c2722", linecolor="#2c2722",
                             tickfont=dict(size=11, color="#8a7d68", family="Orbitron, sans-serif")),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Rajdhani, sans-serif", color="#8a7d68"),
        legend=dict(font=dict(color="#8a7d68", family="Orbitron, sans-serif", size=11),
                    orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
        height=400, margin=dict(l=60, r=60, t=30, b=50),
    )
    return fig


def neo_radar_chart(stats_a, stats_b, label_a, label_b):
    """Radar chart comparing two periods (Tokyo Neo only)."""
    categories = ["Distance", "Runs", "Speed", "Cadence", "Elevation", "Calories"]

    def get_vals(s):
        pace = s["Avg Pace"]
        return [
            s["Total km"],
            s["Runs"],
            1 / pace if pd.notna(pace) and pace > 0 else 0,
            s.get("Avg Cadence", 0) or 0,
            s["Total Elevation"] or 0,
            s["Total Calories"] or 0,
        ]

    raw_a, raw_b = get_vals(stats_a), get_vals(stats_b)

    # Normalize 0-100
    norm_a, norm_b = [], []
    for va, vb in zip(raw_a, raw_b):
        mx = max(abs(va), abs(vb))
        if mx > 0:
            norm_a.append(va / mx * 100)
            norm_b.append(vb / mx * 100)
        else:
            norm_a.append(50)
            norm_b.append(50)

    fig = go.Figure()
    for vals, name, color, fill in [
        (norm_a, label_a, "#00f0ff", "rgba(0,240,255,0.08)"),
        (norm_b, label_b, "#ff2d78", "rgba(255,45,120,0.08)"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill="toself", name=name,
            line=dict(color=color, width=2), fillcolor=fill,
            marker=dict(size=5),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 105], gridcolor="#21262d",
                            linecolor="#21262d", tickfont=dict(size=8, color="#484f58")),
            angularaxis=dict(gridcolor="#21262d", linecolor="#21262d",
                             tickfont=dict(size=11, color="#8b949e", family="Sora, sans-serif")),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#8b949e"),
        legend=dict(font=dict(color="#8b949e", family="Sora, sans-serif", size=11),
                    orientation="h", yanchor="bottom", y=-0.15, x=0.5, xanchor="center"),
        height=400, margin=dict(l=60, r=60, t=30, b=50),
    )
    return fig


# ── Load Data ─────────────────────────────────────────

@st.cache_data(ttl=60)
def load_data():
    return load_dataframe()


df = load_data()

# ── Header ────────────────────────────────────────────

activity_count = len(df) if not df.empty else 0
year_range = ""
if not df.empty:
    y1 = df["start_time"].min().year
    y2 = df["start_time"].max().year
    year_range = f"{y1}\u2013{y2}" if y1 != y2 else str(y1)

if theme == "Art Deco":
    st.markdown(f"""<div class="deco-header">
        <div class="deco-ornament"><span class="deco-diamond sm"></span><span class="deco-line"></span>
        <span class="deco-diamond gold"></span><span class="deco-diamond lg"></span>
        <span class="deco-diamond gold"></span><span class="deco-line"></span>
        <span class="deco-diamond sm"></span></div>
        <div class="deco-title">Garmin Running</div>
        <div class="deco-subtitle">Performance Dashboard</div>
        <div class="deco-ornament"><span class="deco-diamond sm"></span><span class="deco-line"></span>
        <span class="deco-diamond gold"></span><span class="deco-diamond lg"></span>
        <span class="deco-diamond gold"></span><span class="deco-line"></span>
        <span class="deco-diamond sm"></span></div>
        <div class="deco-meta">{activity_count:,} activities \u00b7 {year_range}</div>
    </div>""", unsafe_allow_html=True)
elif theme == "Tokyo Neo":
    st.markdown(f"""<div class="neo-header">
        <div class="neo-header-line"></div>
        <div class="neo-dots"><span class="neo-dot"></span>
        <span class="neo-dot" style="animation-delay:0.3s;"></span>
        <span class="neo-dot" style="animation-delay:0.6s;"></span></div>
        <div class="neo-title">GARMIN <span class="neo-accent">RUNNING</span></div>
        <div class="neo-subtitle">// performance dashboard</div>
        <div class="neo-dots"><span class="neo-dot" style="animation-delay:0.9s;"></span>
        <span class="neo-dot" style="animation-delay:0.6s;"></span>
        <span class="neo-dot" style="animation-delay:0.3s;"></span></div>
        <div class="neo-header-line"></div>
        <div class="neo-meta">{activity_count:,} activities \u00b7 {year_range}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""<div class="br-header">
        <div class="br-scanline"></div>
        <div class="br-scanline dim"></div>
        <div class="br-title">GARMIN <span class="br-accent">RUNNING</span></div>
        <div class="br-subtitle"><span class="br-bracket">[</span> performance dashboard <span class="br-bracket">]</span></div>
        <div class="br-scanline dim"></div>
        <div class="br-scanline"></div>
        <div class="br-meta">{activity_count:,} activities \u00b7 {year_range}</div>
    </div>""", unsafe_allow_html=True)

if df.empty:
    st.warning("No data yet. Run `python pull_activities.py running` to pull activities.")
    st.stop()


# ── Latest Run ────────────────────────────────────────

latest = df.iloc[-1]
date_str = latest["start_time"].strftime("%b %d, %Y").upper()
st.markdown(f'<div class="latest-date">Latest Run \u2014 {date_str}</div>', unsafe_allow_html=True)

pace_m = int(latest["pace_min_km"])
pace_s = int((latest["pace_min_km"] % 1) * 60)
dur_m = int(latest["duration_min"])
dur_s = int(latest["duration_s"] % 60)

row1 = [
    ("Distance", f"{latest['distance_km']:.2f}", "km"),
    ("Duration", f"{dur_m}:{dur_s:02d}", "min"),
    ("Pace", f"{pace_m}:{pace_s:02d}", "/km"),
    ("Calories", f"{latest['calories']:.0f}", "kcal"),
]
html = '<div class="metric-grid">'
for label, val, unit in row1:
    html += (f'<div class="m-card"><div class="m-label">{label}</div>'
             f'<div class="m-val">{val}<span class="m-unit">{unit}</span></div></div>')
html += '</div>'
st.markdown(html, unsafe_allow_html=True)

row2 = []
if pd.notna(latest["avg_hr"]):
    row2.append(("Avg HR", f"{latest['avg_hr']:.0f}", "bpm"))
if pd.notna(latest["max_hr"]):
    row2.append(("Max HR", f"{latest['max_hr']:.0f}", "bpm"))
if pd.notna(latest["elevation_gain"]):
    row2.append(("Elevation", f"+{latest['elevation_gain']:.0f}", "m"))
if pd.notna(latest["cadence"]):
    row2.append(("Cadence", f"{latest['cadence']:.0f}", "spm"))

if row2:
    html2 = f'<div class="metric-grid" style="grid-template-columns: repeat({len(row2)}, 1fr);">'
    for label, val, unit in row2:
        html2 += (f'<div class="m-card"><div class="m-label">{label}</div>'
                  f'<div class="m-val">{val}<span class="m-unit">{unit}</span></div></div>')
    html2 += '</div>'
    st.markdown(html2, unsafe_allow_html=True)

# Visual board comparing latest run to averages
if theme == "Tokyo Neo":
    neo_visual_board(latest, df)
elif theme == "Blade Runner 2049":
    br_visual_board(latest, df)

divider()


# ── Time Range ────────────────────────────────────────

range_options = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "All Time": None}
_rl, _rr = st.columns([1, 4])
with _rl:
    selected_range = st.selectbox("Time Range", list(range_options.keys()), index=4,
                                  label_visibility="collapsed")
days = range_options[selected_range]

if days:
    cutoff = df["start_time"].max() - pd.Timedelta(days=days)
    filtered_df = df[df["start_time"] >= cutoff]
else:
    filtered_df = df

st.caption(f"{len(filtered_df)} activities" + (f" \u00b7 last {days} days" if days else " \u00b7 all time"))


# ── Tabs ──────────────────────────────────────────────

tab_trends, tab_summary, tab_compare, tab_zones = st.tabs(["Trends", "Summary", "Compare", "Zones"])

# ── Trends ────────────────────────────────────────────

with tab_trends:
    t1, t2, t3, t4 = st.tabs(["Distance & Pace", "Heart Rate", "Effort", "Cadence & Elevation"])

    with t1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_chart(filtered_df, "start_time", "distance_km",
                                       "Distance", "km", CC["dist"]), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart(filtered_df, "start_time", "pace_min_km",
                                       "Pace", "min/km", CC["pace"]), use_container_width=True)
    with t2:
        st.plotly_chart(make_dual_chart(filtered_df, "start_time", "avg_hr", "max_hr",
                                        "Heart Rate", "Avg HR", "Max HR", "bpm",
                                        CC["hr1"], CC["hr2"]), use_container_width=True)
    with t3:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_chart(filtered_df, "start_time", "duration_min",
                                       "Duration", "min", CC["dur"]), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart(filtered_df, "start_time", "calories",
                                       "Calories", "kcal", CC["cal"]), use_container_width=True)
    with t4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_chart(filtered_df, "start_time", "cadence",
                                       "Cadence", "spm", CC["cad"]), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart(filtered_df, "start_time", "elevation_gain",
                                       "Elevation Gain", "m", CC["elev"]), use_container_width=True)

# ── Summary ───────────────────────────────────────────

with tab_summary:
    prs = personal_records(filtered_df)
    section_label("Personal Records")

    pr_html = '<div class="pr-grid">'
    if "fastest_pace" in prs:
        pr = prs["fastest_pace"]
        pr_html += (f'<div class="pr-card"><div class="pr-label">Fastest Pace</div>'
                    f'<div class="pr-val">{pr["value"]}</div>'
                    f'<div class="pr-detail">{pr["distance"]} \u00b7 {pr["date"]}</div></div>')
    if "longest_run" in prs:
        pr = prs["longest_run"]
        pr_html += (f'<div class="pr-card"><div class="pr-label">Longest Run</div>'
                    f'<div class="pr-val">{pr["value"]}</div>'
                    f'<div class="pr-detail">{pr["pace"]} \u00b7 {pr["date"]}</div></div>')
    if "most_elevation" in prs:
        pr = prs["most_elevation"]
        pr_html += (f'<div class="pr-card"><div class="pr-label">Most Elevation</div>'
                    f'<div class="pr-val">{pr["value"]}</div>'
                    f'<div class="pr-detail">{pr["distance"]} \u00b7 {pr["date"]}</div></div>')
    pr_html += '</div>'
    st.markdown(pr_html, unsafe_allow_html=True)

    divider()

    section_label("Monthly Summary")
    monthly = monthly_summary(filtered_df)
    monthly.columns = ["Runs", "Total km", "Total min", "Avg Pace", "Avg Cadence",
                        "Avg HR", "Elevation (m)", "Calories"]
    st.dataframe(monthly, use_container_width=True)

    section_label("Weekly Summary")
    weekly = weekly_summary(filtered_df)
    weekly.columns = ["Runs", "Total km", "Total min", "Avg Pace", "Avg Cadence",
                       "Avg HR", "Elevation (m)", "Calories"]
    st.dataframe(weekly, use_container_width=True)

# ── Compare ───────────────────────────────────────────

with tab_compare:
    section_label("Compare Two Periods")

    min_date = df["start_time"].min().date()
    max_date = df["start_time"].max().date()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f'<div class="sec-label" style="font-size:0.7rem;">Period A</div>',
                    unsafe_allow_html=True)
        a_start = st.date_input("Start", value=max_date - pd.Timedelta(days=60),
                                min_value=min_date, max_value=max_date, key="a_start")
        a_end = st.date_input("End", value=max_date - pd.Timedelta(days=30),
                              min_value=min_date, max_value=max_date, key="a_end")
    with col_b:
        st.markdown(f'<div class="sec-label" style="font-size:0.7rem;">Period B</div>',
                    unsafe_allow_html=True)
        b_start = st.date_input("Start", value=max_date - pd.Timedelta(days=30),
                                min_value=min_date, max_value=max_date, key="b_start")
        b_end = st.date_input("End", value=max_date,
                              min_value=min_date, max_value=max_date, key="b_end")

    period_a = df[(df["start_time"].dt.date >= a_start) & (df["start_time"].dt.date <= a_end)]
    period_b = df[(df["start_time"].dt.date >= b_start) & (df["start_time"].dt.date <= b_end)]

    if period_a.empty or period_b.empty:
        st.warning("One or both periods have no activities. Adjust the date ranges.")
    else:
        def period_stats(p):
            return {
                "Runs": len(p),
                "Total km": p["distance_km"].sum(),
                "Avg km/run": p["distance_km"].mean(),
                "Avg Pace": p["pace_min_km"].mean(),
                "Avg Cadence": p["cadence"].mean(),
                "Total Elevation": p["elevation_gain"].sum(),
                "Total Calories": p["calories"].sum(),
            }

        stats_a = period_stats(period_a)
        stats_b = period_stats(period_b)

        # Radar chart
        if theme == "Tokyo Neo":
            st.plotly_chart(
                neo_radar_chart(stats_a, stats_b,
                                f"A: {a_start}\u2192{a_end}", f"B: {b_start}\u2192{b_end}"),
                use_container_width=True)
        elif theme == "Blade Runner 2049":
            st.plotly_chart(
                br_radar_chart(stats_a, stats_b,
                               f"A: {a_start}\u2192{a_end}", f"B: {b_start}\u2192{b_end}"),
                use_container_width=True)
        else:
            st.plotly_chart(
                deco_radar_chart(stats_a, stats_b,
                                 f"A: {a_start}\u2192{a_end}", f"B: {b_start}\u2192{b_end}"),
                use_container_width=True)

        divider()

        st.caption(f"Period A: {a_start} \u2192 {a_end} ({len(period_a)} runs)  \u00b7  "
                   f"Period B: {b_start} \u2192 {b_end} ({len(period_b)} runs)")

        metrics = [
            ("Runs", "", 0, False),
            ("Total km", "km", 1, False),
            ("Avg km/run", "km", 2, False),
            ("Avg Pace", "min/km", 2, True),
            ("Avg Cadence", "spm", 0, False),
            ("Total Elevation", "m", 0, False),
            ("Total Calories", "kcal", 0, False),
        ]

        for i in range(0, len(metrics), 4):
            row = st.columns(min(4, len(metrics) - i))
            for j, (label, unit, decimals, lower_is_better) in enumerate(metrics[i:i + 4]):
                val_a = stats_a[label]
                val_b = stats_b[label]
                delta = val_b - val_a if pd.notna(val_a) and pd.notna(val_b) else None

                if decimals == 0:
                    display_b = f"{val_b:.0f} {unit}".strip()
                    delta_str = f"{delta:+.0f}" if delta is not None else None
                else:
                    display_b = f"{val_b:.{decimals}f} {unit}".strip()
                    delta_str = f"{delta:+.{decimals}f}" if delta is not None else None

                delta_inv = "inverse" if lower_is_better else "normal"
                row[j].metric(label, display_b, delta=delta_str, delta_color=delta_inv)

# ── Zones ────────────────────────────────────────────

with tab_zones:
    # Classify each activity into a pace zone
    zdf = filtered_df.dropna(subset=["pace_min_km"]).copy()
    zdf["pace_zone"] = pd.cut(zdf["pace_min_km"], bins=ZONE_BINS, labels=ZONE_LABELS, right=True)

    zone_counts = zdf["pace_zone"].value_counts().reindex(ZONE_LABELS, fill_value=0)
    zone_km = zdf.groupby("pace_zone", observed=True)["distance_km"].sum().reindex(ZONE_LABELS, fill_value=0)
    total = zone_counts.sum()

    # ── Zone summary cards ──
    section_label("Pace Zone Breakdown")

    zone_card_html = '<div class="metric-grid">'
    for label, color in zip(ZONE_LABELS, ZONE_COLORS):
        count = int(zone_counts.get(label, 0))
        pct = count / total * 100 if total else 0
        zone_card_html += (
            f'<div class="m-card">'
            f'<div class="m-label" style="color:{color}">{label}</div>'
            f'<div class="m-val">{count}<span class="m-unit"> runs</span></div>'
            f'<div style="font-size:0.75rem;color:{DIM}">{pct:.0f}% · {zone_km.get(label, 0):.0f} km</div>'
            f'</div>'
        )
    zone_card_html += '</div>'
    st.markdown(zone_card_html, unsafe_allow_html=True)

    divider()

    # ── Row 1: Donut + Bar ──
    col_donut, col_bar = st.columns(2)

    with col_donut:
        fig_donut = go.Figure(data=[go.Pie(
            labels=ZONE_LABELS, values=zone_counts.values,
            hole=0.55, marker=dict(colors=ZONE_COLORS, line=dict(color=BG, width=2)),
            textinfo="percent", textfont=dict(family=FONT_B, size=12, color=TXT),
            hovertemplate="<b>%{label}</b><br>%{value} runs (%{percent})<extra></extra>",
            sort=False,
        )])
        fig_donut.update_layout(
            title=dict(text="ZONE DISTRIBUTION", font=dict(family=FONT_H, size=13, color=TXT),
                       x=0.5, xanchor="center"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG,
            font=dict(family=FONT_B, color=DIM, size=11),
            height=380, margin=dict(l=20, r=20, t=50, b=30),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5,
                        font=dict(color=DIM, family=FONT_B, size=10)),
            hoverlabel=dict(bgcolor=SURFACE, bordercolor=PRIMARY,
                            font=dict(color=TXT, family=FONT_B, size=12)),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_bar:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=ZONE_LABELS, x=zone_counts.values, orientation="h",
            marker=dict(color=ZONE_COLORS, line=dict(color=BG, width=1)),
            text=[f"{zone_km[z]:.0f} km" for z in ZONE_LABELS],
            textposition="outside", textfont=dict(family=FONT_B, size=10, color=DIM),
            hovertemplate="<b>%{y}</b><br>%{x} runs<extra></extra>",
        ))
        layout_bar = _layout("Runs per zone", "runs")
        layout_bar["yaxis"] = dict(autorange="reversed", tickfont=dict(color=TXT, size=11, family=FONT_B),
                                   gridcolor=GRID, linecolor=BORDER)
        layout_bar["xaxis"]["title"] = dict(text="runs", font=dict(size=11, color=DIM))
        layout_bar["height"] = 380
        fig_bar.update_layout(**layout_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

    divider()

    # ── Row 2: Yearly zone trend ──
    section_label("Zone Trend by Year")

    zdf["year"] = zdf["start_time"].dt.year
    yearly_zones = zdf.groupby(["year", "pace_zone"], observed=True).size().unstack(fill_value=0)
    yearly_zones = yearly_zones.reindex(columns=ZONE_LABELS, fill_value=0)
    yearly_pct = yearly_zones.div(yearly_zones.sum(axis=1), axis=0) * 100

    fig_trend = go.Figure()
    for label, color in zip(ZONE_LABELS, ZONE_COLORS):
        fig_trend.add_trace(go.Bar(
            x=yearly_pct.index.astype(str), y=yearly_pct[label],
            name=label, marker=dict(color=color, line=dict(color=BG, width=0.5)),
            hovertemplate=f"<b>{label}</b><br>%{{y:.0f}}% of runs<extra></extra>",
        ))
    layout_trend = _layout("Zone mix by year", "% of runs")
    layout_trend["barmode"] = "stack"
    layout_trend["legend"] = dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5,
                                  font=dict(color=DIM, family=FONT_H, size=10))
    layout_trend["height"] = 420
    layout_trend["margin"] = dict(l=50, r=20, t=80, b=30)
    fig_trend.update_layout(**layout_trend)
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Theme Selector (bottom of page) ─────────────────
divider()
_left, _center, _right = st.columns([2, 1, 2])
with _center:
    st.selectbox("Theme", ["Art Deco", "Tokyo Neo", "Blade Runner 2049"],
                 index=["Art Deco", "Tokyo Neo", "Blade Runner 2049"].index(theme),
                 key="theme", label_visibility="collapsed")
