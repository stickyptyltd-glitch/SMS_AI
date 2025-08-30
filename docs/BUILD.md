# Build & Packaging

## Quick Start
- Setup: `make setup`
- Tests: `make test`
- Run API: `make run`

## Docker Images
- Webhooks: `make docker-build-webhooks`
- Issuer: `make docker-build-issuer`
- Compose (prod-style): `make compose`

## Licensing
- Issue later (Dockerized):
  - `LICENSE_ISSUER_SECRET=<base64> scripts/issue_license.sh --license-id LIC-123 --tier pro --expires 2026-12-31 --hardware-id ANY --features core,assist`
- Activate on host:
  - `curl -X POST http://<host>:8081/license/activate -H 'Content-Type: application/json' -d '{"key":"<TOKEN>"}'`

## Versioning
- Current version: see `VERSION`.
- Tag releases as `v$(cat VERSION)` and use `docs/RELEASE_TEMPLATE.md` for notes.

## Android Gradle Wrapper
- If you prefer local builds via `./gradlew`, bootstrap the wrapper (requires Gradle installed):
  - `scripts/bootstrap_gradle_wrapper.sh 8.7`
- Then run: `./gradlew bundleStoreRelease` or use Android Studio.
