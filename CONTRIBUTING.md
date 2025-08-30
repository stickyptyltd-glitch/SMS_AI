# Contributing

Thank you for helping improve DayleSMS AI. Please follow these guidelines to keep changes focused and smooth.

## Quick Links
- Contributor guide: `AGENTS.md`
- Onboarding (build, license, ship): `docs/ONBOARDING.md`
- Build & packaging: `docs/BUILD.md`
- Runbook (ops): `docs/RUNBOOK.md`
- Release checklist (issue template): `.github/ISSUE_TEMPLATE/release.md`

## Code Style
- Python: PEP 8, 4 spaces, type hints where reasonable.
- Kotlin/Android: idiomatic Kotlin, keep functions small; use existing patterns.
- Naming: `snake_case` for Python, `camelCase`/`PascalCase` for Kotlin.

## Tests
- Pytest for server (`tests/`). Prefer mocking network calls.
- Add tests for new branches in `ai/` or `server.py` when you change logic.

## PRs
- Keep changes scoped; explain problem, approach, tradeoffs.
- Update docs (`README.md`, `.env.example`) if config changes.
- Include screenshots for Android UI tweaks.

## Security
- Do not commit secrets. Use env vars (`LICENSE_ISSUER_SECRET`) and `.env`.
- Be cautious around licensing and token handling.
