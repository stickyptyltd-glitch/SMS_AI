# Release v1.0.0

## Summary
Initial production release with offline license activation, hardened endpoints, CI, Dockerized issuer, and complete contributor/ops docs.

## Changes
- Licensing: HS256 offline activation tokens; encrypted on disk; hardware binding; endpoints `/license/activate`, `/license/status`, `/license/hwid`; enforcement via `LICENSE_ENFORCE=1`.
- Security: Request timeouts, TwiML escaping, Messenger signature verification; structured logs via `LOG_FORMAT=json`.
- API: Added `/health` liveness endpoint.
- Build & CI: GitHub Actions CI on PRs; Makefile targets (`setup`, `test`, `run`, image builds, `compose`); `VERSION` file.
- Docker: Added `docker/license-issuer` image; `docker-compose.yml` enforces licensing for webhooks.
- Docs: README updates; AGENTS.md; docs for BUILD, MANUAL, RUNBOOK, RELEASE_TEMPLATE, GitHub workflow; marketing pack scaffolds.

## Breaking Changes
- New env vars: `LICENSE_ENFORCE` (default 0), `LICENSE_ISSUER_SECRET` (base64). Configure before production deployment.

## Images
- Build locally:
  - `smsai-twilio:latest` from `docker/twilio-webhook`
  - `smsai-msgr:latest` from `docker/messenger-webhook`
  - `smsai-license-issuer:latest` from `docker/license-issuer`
- Publish under your registry as `:v1.0.0` and record digests in the GitHub Release.

## Licensing Notes
- Issue tokens post-packaging: `LICENSE_ISSUER_SECRET=<base64> scripts/issue_license.sh --license-id LIC-123 --tier pro --expires 2026-12-31 --hardware-id ANY --features core,assist`.
- Bind to host HWID via `GET /license/hwid` and pass `--hardware-id <HWID>`.

## Migration Steps
- Add `LICENSE_ENFORCE` and `LICENSE_ISSUER_SECRET` to production environment.
- Build/push images, update compose stack, activate license on each host.

## Verification
- Health: `GET /health` returns `{ ok: true }`.
- Licensing: `GET /license/status` shows `status: valid` after activation.
- Functional: `/reply` and `/assist` work under enforcement with a valid license.

## Rollback
- Re-deploy v0.1.0 images (or previous tag) and restore prior configuration.
