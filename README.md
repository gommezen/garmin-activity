# Garmin Activity Puller

A Python CLI that pulls your running activities from Garmin Connect, stores them in SQLite, and visualizes trends via a Streamlit dashboard or Jupyter notebook.

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
ui/             Streamlit dashboard
notebooks/      Jupyter analysis notebook
data/           SQLite database and auth tokens (gitignored)
output/         CSV and JSON exports (gitignored)
```
