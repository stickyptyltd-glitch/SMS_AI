# Repository Guidelines

> Concise contributor guide for SMS_AI.

## Project Structure & Module Organization
- `ai/`: Core analysis, reply generation, summaries. Prefer small, pure, unit‑testable funcs.
- `server.py`: Flask API orchestration; persists runtime data in `synapseflow_data/`.
- `test_client.py`: Dev CLI + local webhooks (Twilio, Messenger, KDE Connect).
- `tests/`: Pytest suite (`test_*.py`).
- `docker/`, `docker-compose.yml`: Production‑style webhook images.
- `app/`: Android SMS AutoReply (built separately via Gradle).
- `.env.example`: Copy to `.env` and fill tokens/secrets.

## Build, Test, and Development Commands
- Create venv + install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-test-client.txt`
- Run local server (uses `OLLAMA_URL`, `OLLAMA_MODEL`): `python server.py`
- Run tests (verbose): `pytest -v`
- Start Twilio webhook (dev): `python test_client.py --verbose twilio webhook --host 0.0.0.0 --port 5005`
- Start Messenger webhook (dev): `python test_client.py --verbose messenger webhook --host 0.0.0.0 --port 5006`
- Docker (prod-style webhooks): `docker compose up --build`

## Coding Style & Naming Conventions
- Python 3.11, PEP 8, 4‑space indent, add type hints.
- Naming: `snake_case` (func/vars), `PascalCase` (classes), `UPPER_SNAKE` (constants).
- Avoid side effects at import; keep modules focused. Prefer pure functions in `ai/`.
- Logging: structured; set `LOG_FORMAT=json` for webhooks and server logs.

## Testing Guidelines
- Framework: Pytest; tests live in `tests/` as `test_*.py`.
- Keep tests offline; mock HTTP/Twilio. Run with `pytest -v`.
- Add unit tests for new branches in `ai/` and `server.py`.
- Keep tests deterministic; no external network or secrets.

## Commit & Pull Request Guidelines
- Commits: imperative, concise scope, e.g., `feat(server): add outcome endpoint`.
- Include context: problem, approach, trade‑offs; keep diffs minimal.
- PRs: link issues, describe changes, update tests; update `README.md` and `.env.example` when config changes; include Android UI screenshots when relevant.

## Security & Configuration Tips
- Never commit secrets. Use `.env` (copy from `.env.example`).
- Validate inputs (phone numbers, message text); enforce HTTP timeouts.
- Treat `synapseflow_data/` as runtime state; do not check in.
- Use HTTPS in production; verify Messenger signatures and escape TwiML.

