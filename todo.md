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

## Future Ideas
- [ ] Export to CSV for spreadsheet analysis
- [ ] Add weekly/monthly summary stats (totals, averages, PRs)
- [ ] Plot activity trends over time (matplotlib or plotly)
- [ ] Compare performance across date ranges
- [ ] Auto-download .fit files for deeper analysis
- [ ] Schedule automatic pulls (daily/weekly cron job)
- [ ] Add support for pulling multiple sport types at once
