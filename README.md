SMS_AI Workspace [![Android AAB Build](../../actions/workflows/android-build.yml/badge.svg)](../../actions/workflows/android-build.yml)
================

This workspace includes an Android SMS auto-reply app plus a Python test client with production-ready webhooks for Twilio SMS and Facebook Messenger.

Structure
---------
- `app/`: Android app (Dayle SMS AutoReply)
- `test_client.py`: CLI + webhooks for local server, Twilio, KDE Connect, Messenger
- `requirements-test-client.txt`: Python deps for the CLI/webhooks
- `docker/`: Production Dockerfiles for webhooks
- `docker-compose.yml`: Compose stack to run webhooks

Prereqs
-------
- Python 3.11+
- For Twilio: account SID, auth token, a phone number
- For Messenger: a Facebook App + Page, tokens/secrets
- For KDE Connect: `kdeconnect-cli` installed and a paired device
- Local LLM server: run `server.py` or `server1.py` (Flask) that calls Ollama

Python Setup
------------
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-test-client.txt
```

Local Server
------------
- Env: `DAYLE_SERVER` (default `http://127.0.0.1:8081`)
- Optional: disable model calls with `OLLAMA_DISABLE=1` (uses safe templates/heuristics only)
- Interactive REPL:
```
python test_client.py --verbose interactive --contact "Tester"
```
- One-shot reply:
```
python test_client.py reply "hey, can we talk?" --contact "Courtney"
```
- Feedback:
```
python test_client.py feedback "incoming" "draft" "final" --contact "Tester" --accepted --edited
```
- Profile get/set:
```
python test_client.py profile get
python test_client.py profile set --style-rules "Short, blunt." --preferred-phrases "Ok.;All good." --banned-words "never,maybe"
```

Twilio
------
- Set env vars (see `.env.example`):
  - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`
- Send SMS:
```
python test_client.py twilio send --to +15551230001 --text "Hello" --from +15551230000
```
- Webhook (local dev):
```
python test_client.py --verbose twilio webhook --host 0.0.0.0 --port 5005 --auto --from +15551230000
```
Expose via HTTPS (e.g., ngrok) and set Twilio Messaging webhook to `https://your-domain/sms`.

Messenger
---------
- Set env vars (see `.env.example`):
  - `FB_VERIFY_TOKEN`, `FB_APP_SECRET`, `FB_PAGE_TOKEN`
- Webhook (local dev):
```
python test_client.py --verbose messenger webhook --host 0.0.0.0 --port 5006 --auto
```
Expose publicly via HTTPS and configure webhook in the Meta App dashboard (`/webhook`).
- Send via Graph API:
```
python test_client.py messenger send --psid 1234567890123456 --text "Hello via Page"
```

KDE Connect
-----------
- List devices:
```
python test_client.py kde devices
```
- Send SMS:
```
python test_client.py kde send --device-id abcdef1234567890 --to +15551230002 --text "Hello from KDE Connect"
```
- Watch notifications:
```
python test_client.py kde watch --device-id abcdef1234567890 --interval 5
```

Docker (production webhooks)
----------------------------
- Build images:
```
docker build -t smsai-twilio docker/twilio-webhook
docker build -t smsai-msgr docker/messenger-webhook
```
- Run Twilio webhook:
```
docker run --rm -p 5005:5005 \
  -e TWILIO_FROM=+15551230000 \
  -e DAYLE_SERVER=http://host.docker.internal:8081 \
  -e AUTO_REPLY=1 -e LOG_FORMAT=json \
  smsai-twilio
```
- Run Messenger webhook:
```
docker run --rm -p 5006:5006 \
  -e FB_VERIFY_TOKEN=verifytoken \
  -e FB_APP_SECRET=appsecret \
  -e FB_PAGE_TOKEN=pagetoken \
  -e DAYLE_SERVER=http://host.docker.internal:8081 \
  -e AUTO_REPLY=1 -e LOG_FORMAT=json \
  smsai-msgr
```

Compose
-------
Populate `.env` (copy from `.env.example`), then:
```
docker compose up --build
```

Admin Panel
-----------
- Open `http://localhost:8081/admin` to manage profile, memory, and license.
- Protect in production by setting `ADMIN_TOKEN=<secret>` and include it via header `X-Admin-Token` or query `?token=...`.
- Login helper: `http://localhost:8081/admin/login` stores the token in the browser and redirects to `/admin`.

Rate Limiting
-------------
- Default per‑IP limit: `RATE_LIMIT_PER_MIN=120` requests/minute (set via env).
- Applies to `/reply`, `/assist`, `/feedback`, and `/outcome`.

Security & Hardening
--------------------
- Input validation for phone numbers and message content
- Strict connect/read timeouts on all HTTP requests
- TwiML XML escaping
- Messenger signature verification (HMAC SHA-256) when `FB_APP_SECRET` is set
- Structured logging with `LOG_FORMAT=json`

Notes
-----
- Ensure your device can reach the local Flask server (`DAYLE_SERVER`); on Android use device-accessible IP (not 127.0.0.1).
- KDE notification watcher is best-effort; deeper receive automation would require a dedicated bridge.

Licensing (Enterprise)
----------------------
- Enable enforcement: set `LICENSE_ENFORCE=1`.
- Provide secret via env: set `LICENSE_ISSUER_SECRET` (base64) in production; do not commit secrets.
- Issue a key (offline): `python tools/license_issuer.py --license-id LIC-001 --tier pro --expires 2025-12-31 --hardware-id ANY --features core,assist`.
- Activate: `POST /license/activate` with `{ "key": "<the token from issuer>" }`.
- Status: `GET /license/status`. License is hardware‑bound and stored as `.dayle_license`.
 - Get hardware ID (for binding): `GET /license/hwid`.

Build & Ops
-----------
- Make targets: `make setup | test | run | docker-build-webhooks | docker-build-issuer | compose`
- More: see `docs/BUILD.md`, `docs/RUNBOOK.md`, and `docs/RELEASE_TEMPLATE.md`.
- Metrics: see `docs/METRICS.md`; scrape `GET /metrics`.

Release Shortcuts
-----------------
- Run Android AAB Build (store/full): ../../actions/workflows/android-build.yml
- Open Release Checklist issue: ../../issues/new?assignees=&labels=release&template=release.md&title=Release+vX.Y.Z
