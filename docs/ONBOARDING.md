# Onboarding — Build, License, and Ship

## 1) Server (local or prod)
- Setup: `make setup && make run` (or `docker compose up --build`).
- Env: set `LICENSE_ENFORCE=1` and `LICENSE_ISSUER_SECRET=<base64>` in prod.
- Activate: `POST /license/activate` with token; verify `GET /license/status`.
- Health/Metrics: `GET /health`, `GET /metrics`.

## 2) Privacy Policy (public URL)
- GitHub Pages: Settings → Pages → Deploy from branch → `main` /docs.
- Use URL: `https://<user>.github.io/<repo>/privacy_policy.html` (already in `docs/`).

## 3) Android AAB via CI (fast path)
- Go to Actions → "Android AAB Build" → Run workflow.
  - `flavor=store` (Play‑safe) or `full` (non‑Play)
  - `publish=false` to build only
- Download artifacts:
  - `aab-store-release-signed` — upload this to Play
  - `upload-keystore-and-credentials` — JKS + passwords (keep secure)

## 4) Optional: Publish from CI
- Add secret `GPLAY_SERVICE_ACCOUNT_JSON` (service account JSON with Edit releases).
- Run workflow with `publish=true` and `track=internal|beta|production`.
- See `docs/PLAY_CI.md` for details.

## 5) Play Console
- Listing copy: `docs/PLAY_LISTING.md`; screenshots: `docs/PLAY_SHOTS_CHECKLIST.md`.
- Privacy policy URL: GitHub Pages link above.
- Data Safety: declare local storage of message content; no sale.
- Upload AAB (internal testing), test, then staged rollout.

## 6) Android Studio (optional local builds)
- Open project → select build variant `storeRelease` → Generate Signed Bundle/APK.
- Signing: see `docs/ANDROID_SIGNING.md`.

## 7) Licensing Tokens (later)
- Issue: `LICENSE_ISSUER_SECRET=<base64> scripts/issue_license.sh --license-id LIC-123 --tier pro --expires 2027-12-31 --hardware-id ANY --features core,assist`
- Host‑bound: get HWID via `GET /license/hwid` and use `--hardware-id <HWID>`.

## Support
Built by Dayle LeCheyne Stueven — st1cky.pty.ltd. Refer to `docs/RUNBOOK.md` for operations.
