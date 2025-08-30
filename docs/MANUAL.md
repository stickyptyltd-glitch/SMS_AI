# DayleSMS AI — Enterprise Manual

## Overview
DayleSMS AI combines an Android SMS auto‑reply app with a Python service that analyzes incoming messages and drafts respectful, concise replies.

## Activation & Licensing
- Require license in production: set `LICENSE_ENFORCE=1`.
- Provide issuer secret via env (base64): `export LICENSE_ISSUER_SECRET=...`.
- Issue a key offline:
  - `python tools/license_issuer.py --license-id LIC-001 --tier pro --expires 2025-12-31 --hardware-id ANY --features core,assist`
  - Copy the printed token.
- Activate on the server:
  - `curl -X POST http://localhost:8081/license/activate -H 'Content-Type: application/json' -d '{"key":"<TOKEN>"}'`
  - Check status: `curl http://localhost:8081/license/status`
- License is hardware‑bound and encrypted on disk as `.dayle_license`.
- Get hardware ID (to bind a license): `curl http://localhost:8081/license/hwid`

### Issue After Packaging (recommended)
- Build local issuer image once: `docker build -t smsai-license-issuer docker/license-issuer`
- Issue with secret at runtime:
  - `LICENSE_ISSUER_SECRET=base64... docker run --rm -e LICENSE_ISSUER_SECRET=s3cr3t smsai-license-issuer --license-id LIC-002 --tier pro --expires 2026-12-31 --hardware-id ANY --features core,assist`
- Or via helper script: `LICENSE_ISSUER_SECRET=base64... scripts/issue_license.sh --license-id LIC-002 --tier pro --expires 2026-12-31 --hardware-id ANY --features core,assist`

## Running Locally
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-test-client.txt`
- Start API: `python server.py` (set `OLLAMA_URL` and `OLLAMA_MODEL` as needed)
- Test client (interactive): `python test_client.py --verbose interactive --contact "Tester"`

## Security & Anti‑Tamper
- License data: encrypted (Fernet) and server‑validated periodically.
- Request signatures: HMAC on license server calls.
- Webhooks: validate Messenger signatures; escape TwiML; enforce HTTP timeouts.
- Android: enable R8/ProGuard; avoid hard‑coding secrets; load from secure storage.

## Packaging
- Server: use `gunicorn` for webhooks; Docker images in `docker/` and `docker-compose.yml`.
- Android: build via Gradle (`app/`). Sign release builds and keep keystore secure.

## Support
Built by Dayle LeCheyne Stueven — st1cky.pty.ltd. For enterprise support and license management, contact your account representative.
