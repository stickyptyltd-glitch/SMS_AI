# Release Template (vX.Y.Z)

## Summary
- Short description of changes and goals.

## Changes
- Feature 1
- Fix 2
- Docs 3

## Breaking Changes
- Note any config/env migrations.

## Images
- Webhooks: `smsai-twilio@sha256:<digest>`, `smsai-msgr@sha256:<digest>`
- Issuer: `smsai-license-issuer@sha256:<digest>`

## Licensing Notes
- Enforcement: `LICENSE_ENFORCE=1` in production.
- Token issuance: use `scripts/issue_license.sh` with `LICENSE_ISSUER_SECRET`.
- Hardware binding: get HWID via `GET /license/hwid`.

## Migration Steps
- Update `.env` keys if any; rotate secrets if required.
- Pull new images and restart.

## Verification
- Health: `/health` endpoints if exposed; smoke test `/reply` and `/assist`.
- Licensing: `GET /license/status` returns `valid`.

## Rollback
- Re-deploy previous tag images and revert config changes.
