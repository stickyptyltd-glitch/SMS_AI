# Operations Runbook

## Prereqs
- Python 3.11, Docker/Compose, issuer secret (base64) in your secret manager.
- Env: `LICENSE_ENFORCE=1`, `LICENSE_ISSUER_SECRET=<base64>`, messaging creds in `.env`.

## Start Services
- Local API: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-test-client.txt && python server.py`
- Webhooks (prod-style): `docker compose up --build` (uses `.env`).

## Licensing
- Get HWID: `curl http://<host>:8081/license/hwid`
- Issue ANY-bound token:
  - `LICENSE_ISSUER_SECRET=$SECRET scripts/issue_license.sh --license-id LIC-xxx --tier pro --expires 2026-12-31 --hardware-id ANY --features core,assist`
- Issue HWID-bound token:
  - `LICENSE_ISSUER_SECRET=$SECRET scripts/issue_license.sh --license-id LIC-yyy --tier pro --expires 2026-12-31 --hardware-id <HWID> --features core,assist`
- Activate: `curl -X POST http://<host>:8081/license/activate -H 'Content-Type: application/json' -d '{"key":"<TOKEN>"}'`
- Verify: `curl http://<host>:8081/license/status`

## Rotation
- Set new `LICENSE_ISSUER_SECRET`; re‑issue tokens; activate on hosts; revoke old secret.

## Backup/Restore
- Backup `.dayle_license` and `dayle_data/`.
- Restore on same host (HWID-bound) or issue ANY-bound if moving hosts.

## Monitoring
- Watch 403s on `/reply` or `/assist` for license issues.
- Prefer `LOG_FORMAT=json` and ship logs to your aggregator.
