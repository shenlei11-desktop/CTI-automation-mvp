#!/usr/bin/env bash
# Starts the backend (uvicorn) and frontend (vite) together for local dev.
# One-time setup first (see README "Option B"): create .venv + pip install +
# spacy download, and `npm install` in frontend/.
set -e
trap 'kill $(jobs -p) 2>/dev/null' EXIT

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
uvicorn app.main:app --reload &

cd frontend
npm run dev
