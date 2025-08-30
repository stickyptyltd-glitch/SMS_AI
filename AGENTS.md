# Repository Guidelines

## Project Structure & Module Organization
- `ai/`: Analysis, reply generation, and summaries.
- `server.py`: Flask API that analyzes, drafts, and stores memory in `dayle_data/`.
- `test_client.py`: CLI + local webhooks (Twilio, Messenger, KDE Connect).
- `tests/`: Pytest suite (`test_*.py`).
- `docker/` + `docker-compose.yml`: Production Docker images for webhooks.
- `app/`: Android SMS AutoReply app (separate build via Gradle).
- `.env.example`: Copy to `.env` to configure tokens/secrets.

## Build, Test, and Development Commands
- Create venv and install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-test-client.txt`
- Run local server (uses `OLLAMA_URL`, `OLLAMA_MODEL`): `python server.py`
- Run tests (verbose, short trace): `pytest`
- Start Twilio webhook (dev): `python test_client.py --verbose twilio webhook --host 0.0.0.0 --port 5005`
- Start Messenger webhook (dev): `python test_client.py --verbose messenger webhook --host 0.0.0.0 --port 5006`
- Docker compose (production-style webhooks): `docker compose up --build`

## Coding Style & Naming Conventions
- Python 3.11; PEP 8; 4‑space indentation; prefer type hints.
- Names: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- Keep modules focused; avoid side effects at import; prefer small pure functions in `ai/`.
- Logging: prefer structured logs for webhooks (`LOG_FORMAT=json`).

## Testing Guidelines
- Framework: Pytest. Config in `pytest.ini` (`tests/`, `test_*.py`, `Test*` classes, `test_*` functions).
- Run locally: `pytest -v`. Do not require network; mock HTTP/Twilio where possible.
- Add unit tests with clear arrange/act/assert; cover new branches in `ai/` and `server.py`.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise scope, e.g., `feat(server): add outcome endpoint`.
- Include context: problem, approach, and any trade‑offs.
- PRs: link issues, describe changes, include test updates, and screenshots for Android UI when relevant.
- Keep diffs minimal; update `README.md` and `.env.example` when changing configuration.

## Security & Configuration Tips
- Never commit secrets. Use `.env` (see `.env.example`).
- Validate inputs (phone numbers, message text); keep HTTP timeouts.
- Persisted data lives under `dayle_data/`; treat it as runtime state, not source.
- Expose webhooks via HTTPS only in production; verify Messenger signatures and escape TwiML.
