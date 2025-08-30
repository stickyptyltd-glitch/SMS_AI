# CI: Build and Publish to Google Play

## Inputs
- `flavor`: `store` (Play-safe) or `full` (non-Play). Use `store` for Play.
- `publish`: `true` to upload to Play; `false` to only build.
- `track`: `internal`, `alpha`, `beta`, or `production`. Default: `internal`.

## Secrets (optional)
- `STORE_FILE_BASE64`, `STORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`: signs the AAB with your upload key. If omitted, CI will generate an upload keystore and provide it as an artifact.
- `GPLAY_SERVICE_ACCOUNT_JSON`: JSON of a Google Play service account (Edit releases permission). Required to publish.

## Build only
- Actions → Android AAB Build → flavor=store, publish=false → download `aab-store-release-signed`.

## Publish
- Add `GPLAY_SERVICE_ACCOUNT_JSON` secret. Run with `publish=true` and desired `track`.
- CI writes credentials to `gplay.json` and runs `publishStoreReleaseBundle`.

## Notes
- Keep the upload keystore consistent across releases (download artifact and store securely).
- You can later switch to Play App Signing and keep the same upload key.
