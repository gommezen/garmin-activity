# Garmin Activity Puller

A simple Python CLI that pulls your activities from Garmin Connect, displays formatted summaries, and optionally exports to JSON.

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

# Pull the 5 most recent cycling activities from the last 60 days
python pull_activities.py cycling --days 60 --limit 5

# Save raw data to JSON
python pull_activities.py running --save

# List all supported sport types
python pull_activities.py --list-sports
```

