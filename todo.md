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

## Next Steps (pick up here next session)
- [ ] Add Garmin credentials to `.env` file (copy from `.env.example`)
- [ ] Test login: `python pull_activities.py --list-sports`
- [ ] Pull first activity data: `python pull_activities.py running` (or your sport)
- [ ] Try saving to JSON: `python pull_activities.py running --save`

## Future Ideas
- [ ] Export to CSV for spreadsheet analysis
- [ ] Add weekly/monthly summary stats (totals, averages, PRs)
- [ ] Plot activity trends over time (matplotlib or plotly)
- [ ] Compare performance across date ranges
- [ ] Auto-download .fit files for deeper analysis
- [ ] Schedule automatic pulls (daily/weekly cron job)
- [ ] Add support for pulling multiple sport types at once
