#!/usr/bin/env bash
# Start the Shindo API and web dev server together.
set -euo pipefail
cd "$(dirname "$0")"

.venv/bin/uvicorn app.api.main:app --reload --port 8010 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

npm --prefix app/web run dev
