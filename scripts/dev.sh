#!/usr/bin/env bash
# Hot-reload development: API on :8080 (auto-reload) + Vite UI on :5173 (proxies /api).
set -euo pipefail
cd "$(dirname "$0")/.."
source backend/.venv/bin/activate 2>/dev/null || true
(cd backend && uvicorn app.main:app --reload --port 8080) &
API_PID=$!
trap 'kill $API_PID' EXIT
cd frontend && npm run dev
