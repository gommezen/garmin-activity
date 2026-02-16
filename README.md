# Garmin Activity Puller

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-Charts-3F4F75?logo=plotly&logoColor=white)](https://plotly.com)
[![SQLite](https://img.shields.io/badge/SQLite-Storage-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Garmin](https://img.shields.io/badge/Garmin-Connect-007CC3?logo=garmin&logoColor=white)](https://connect.garmin.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Python CLI that pulls your running activities from Garmin Connect, stores them in SQLite, and visualizes trends via a Streamlit dashboard or Jupyter notebook. Features multi-theme UI with Art Deco, Tokyo Neo, and Blade Runner 2049 aesthetics, period comparison, personal records, and animated visual boards.

## Screenshots

### Tokyo Neo Theme
<p align="center">
  <img src="docs/tokyo-neo-header.png" alt="Tokyo Neo — Header, metrics & visual board" width="700">
</p>
<p align="center">
  <img src="docs/tokyo-neo-charts.png" alt="Tokyo Neo — Trend charts" width="700">
</p>

### Blade Runner 2049 Theme
<p align="center">
  <img src="docs/bladerunner.png" alt="Blade Runner 2049 — Dashboard with compare & radar chart" width="700">
</p>
<p align="center">
  <img src="docs/heartrate.png" alt="Blade Runner 2049 — Heart rate trends" width="700">
</p>

## Features

- **Pull** running activities from Garmin Connect with token caching and MFA support
- **Store** in SQLite with automatic deduplication and data cleaning filters
- **Visualize** via interactive Plotly charts (distance, pace, heart rate, cadence, elevation, calories)
- **Themes** — Art Deco (emerald/jade + noir), Tokyo Neo (neon cyan + hot pink), and Blade Runner 2049 (dusty amber + steel blue) with hover effects
- **Compare** any two time periods side-by-side with delta indicators and radar chart
- **Summary** stats — weekly/monthly breakdowns and personal records
- **Export** to CSV or JSON for external analysis

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Add your credentials** — copy `.env.example` to `.env` and fill in your Garmin email and password.

## Usage

```bash
# Pull running activities from the last 30 days
python pull_activities.py running

# Pull with custom range and limit
python pull_activities.py running --days 90 --limit 10

# Export to JSON or CSV
python pull_activities.py running --save
python pull_activities.py running --csv

# Show weekly/monthly summary stats and PRs
python pull_activities.py running --stats

# List all supported sport types
python pull_activities.py --list-sports
```

## Dashboard

```bash
streamlit run ui/dashboard.py
```

## Notebook

```bash
jupyter notebook notebooks/analysis.ipynb
```

## Project Structure

```
src/            Source modules (client, db, display, export, stats)
ui/             Streamlit dashboard with multi-theme support
notebooks/      Jupyter analysis notebook
data/           SQLite database and auth tokens (gitignored)
output/         CSV and JSON exports (gitignored)
docs/           Screenshots and documentation assets
```
