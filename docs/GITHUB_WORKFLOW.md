# GitHub Version Control Walkthrough

## Branching & Releases
- Default branch: `main` for stable. Use `dev/*` for feature branches.
- Tag releases with `vX.Y.Z` and draft GitHub Releases with notes.
- Protect `main`: require PR reviews and CI to pass.

## CI
- Use the included workflow (`.github/workflows/ci.yml`) to run tests on push/PR.
- Add secrets in repo settings (not in code). Use environments for production deploys.

## Ads & Marketing Versioning
- Store marketing assets in `docs/marketing/` and `docs/ads/`.
- Name assets with date + channel + campaign, e.g., `2025-08-30_meta_launch_headlineA.png`.
- Track copy changes in Markdown with PRs; preview diffs for approval.

## Release Checklist
- Bump version in app store metadata and compose images.
- Update `CHANGELOG` in release PR.
- Verify `.env.example` reflects new config.
