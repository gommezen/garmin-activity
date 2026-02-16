# Garmin Activity Puller - TODO

## Completed
- [x] Set up project folder and structure
- [x] Create `pull_activities.py` with sport-type filtering
- [x] Add token caching for persistent login
- [x] Add MFA support
- [x] Add CLI args (--days, --limit, --save, --list-sports)
- [x] Add formatted console output (distance, pace, HR, elevation, etc.)
- [x] Add JSON export (--save flag)
- [x] Install dependencies (garminconnect, python-dotenv)
- [x] Add Garmin credentials to `.env` file
- [x] Test login and pull activity data
- [x] Fix display name showing None on fresh login
- [x] Fix Unicode output on Windows
- [x] Fix --list-sports requiring sport argument
- [x] Add README.md
- [x] Clean up .gitignore
- [x] Add SQLite database with auto-save on pull
- [x] Add Streamlit dashboard with interactive Plotly charts
- [x] Add Jupyter notebook for data exploration
- [x] Replace steps with cadence (spm) — more relevant for running
- [x] Switch charts to Plotly for interactivity (hover, zoom, pan)
- [x] Reorganize project into data-science folder structure (src/, ui/, notebooks/, data/)
- [x] Export to CSV for spreadsheet analysis (--csv flag)
- [x] Add weekly/monthly summary stats and PRs (--stats flag)
- [x] Add Summary tab to Streamlit dashboard
- [x] Add dev_log.json for project memory
- [x] Pull full Garmin history (1,341 activities)
- [x] Add data cleaning filter (removes GPS glitches, fragments, bad pace)
- [x] Add time range selector to dashboard (1mo/3mo/6mo/1yr/all)

- [x] Compare performance across date ranges (Compare tab in dashboard)

## Future Ideas
- [ ] Cannot save jupyter notebook as pdf
[W 2026-02-16 03:11:25.940 ServerApp] 500 GET /nbconvert/pdf/notebooks/analysis.ipynb?download=true (::1): nbconvert failed: xelatex not found on PATH, if you have not installed xelatex you may need to do so. Find further instructions at https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex.
[E 2026-02-16 03:11:25.941 ServerApp] {
    
- [ ] Auto-download .fit files for deeper analysis
- [ ] Schedule automatic pulls (daily/weekly cron job)
- [ ] Add support for pulling multiple sport types at once
