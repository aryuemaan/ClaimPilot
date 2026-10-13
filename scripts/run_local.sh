#!/usr/bin/env bash
# One command local run (macOS / Linux): installs deps, builds the UI, starts the app on :8080.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "ClaimPilot needs Python 3.10+ (3.12 recommended). Found: $(python3 --version)" >&2; exit 1; }

if [[ ! -d backend/.venv ]]; then
  echo "==> Creating Python virtualenv"
  python3 -m venv backend/.venv
fi
source backend/.venv/bin/activate
echo "==> Installing Python packages"
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

if [[ ! -f frontend/dist/index.html || "${REBUILD:-0}" == "1" ]]; then
  echo "==> Building the web app"
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi

[[ -f .env ]] || cp .env.example .env
echo "==> Checking configuration"
(cd backend && python -m app.doctor) || true
echo
echo "==> ClaimPilot running at http://localhost:8080  (customer app: /claim, console: /console)"
cd backend && exec uvicorn app.main:app --host 0.0.0.0 --port 8080
