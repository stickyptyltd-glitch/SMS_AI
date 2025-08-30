#!/usr/bin/env bash
set -euo pipefail

echo "[1/7] Checking dependencies"
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
need python3
need bash

HAS_OLLAMA=0
if command -v ollama >/dev/null 2>&1; then HAS_OLLAMA=1; fi
if command -v docker >/dev/null 2>&1; then HAS_DOCKER=1; else HAS_DOCKER=0; fi

echo "[2/7] Python venv + requirements"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-test-client.txt

echo "[3/7] Ollama model (optional)"
MODEL=${OLLAMA_MODEL:-llama3:8b}
if [ "$HAS_OLLAMA" -eq 1 ]; then
  echo "Ensuring model present: $MODEL"
  set +e
  ollama list | grep -q "^$MODEL" || ollama pull "$MODEL"
  set -e
else
  echo "Ollama not found; skipping pull. Set OLLAMA_URL/MODEL later."
fi

echo "[4/7] .env setup for webhooks"
if [ ! -f .env ]; then
  cp -n .env.example .env || true
  echo "Created .env from .env.example. Please edit credentials."
fi

echo "[5/7] Docker images (optional)"
if [ "$HAS_DOCKER" -eq 1 ]; then
  docker build -t smsai-twilio docker/twilio-webhook || true
  docker build -t smsai-msgr docker/messenger-webhook || true
else
  echo "Docker not found; skipping image builds."
fi

echo "[6/7] Sanity check: run unit tests"
python3 -m unittest discover -s tests -p 'test_*.py' -v || true

echo "[7/7] Optional: run Docker Compose for webhooks"
if [ "${RUN_COMPOSE:-0}" = "1" ] && command -v docker >/dev/null 2>&1; then
  echo "Bringing up docker compose in background..."
  docker compose up -d || true
  echo "Compose is up. Containers listen on 5005 (Twilio) and 5006 (Messenger)."
fi

echo "Starting local Flask server on :8081"
export OLLAMA_URL=${OLLAMA_URL:-http://127.0.0.1:11434/api/generate}
export OLLAMA_MODEL=${OLLAMA_MODEL:-$MODEL}
echo "Launching server.py with OLLAMA_MODEL=$OLLAMA_MODEL"
echo "Use Ctrl+C to stop."
python server.py
