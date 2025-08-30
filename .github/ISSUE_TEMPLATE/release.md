---
name: Release Checklist
about: Track all steps to cut and ship a release
title: "Release vX.Y.Z"
labels: release
assignees: 
  - 
---

## Prep
- [ ] Confirm `VERSION` set to target (e.g., 1.0.1)
- [ ] Update release notes in `docs/RELEASE_NOTES_vX.Y.Z.md`
- [ ] Tag locally and push (`vX.Y.Z`) or confirm tag exists

## Build (Android)
- [ ] Run CI workflow → Android AAB Build → `flavor=store`, `publish=false`
- [ ] Download `aab-store-release-signed` artifact
- [ ] (Optional) Save `upload-keystore-and-credentials` for future releases

## Privacy & Listing
- [ ] GitHub Pages enabled for `/docs`
- [ ] Privacy URL set: `https://<user>.github.io/<repo>/privacy_policy.html`
- [ ] Listing copy reviewed (`docs/PLAY_LISTING.md`)
- [ ] Screenshots prepared (`docs/PLAY_SHOTS_CHECKLIST.md`)
- [ ] Data Safety form reviewed/updated

## Upload to Play
- [ ] Create Internal testing release and upload AAB
- [ ] Add release notes (use `docs/RELEASE_NOTES_vX.Y.Z.md`)
- [ ] Invite testers; complete review checks

## Rollout
- [ ] Promote to production with staged rollout (10–20%)
- [ ] Monitor vitals (crash/ANR), reviews, support channel

## Server & Licensing
- [ ] Ensure `LICENSE_ENFORCE=1` and `LICENSE_ISSUER_SECRET` set in prod
- [ ] Activate/verify license: `/license/activate` → `/license/status`
- [ ] Health/metrics scrape validated (`/health`, `/metrics`)

## Publish (CI, optional)
- [ ] Set `GPLAY_SERVICE_ACCOUNT_JSON` secret
- [ ] Run workflow with `publish=true`, track=`internal|beta|production`

## Post‑Release
- [ ] Create GitHub Release with notes and image digests
- [ ] Update `CHANGELOG` (if used)
- [ ] Open follow‑up tasks (bugs, enhancements)
