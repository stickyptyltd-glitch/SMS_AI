# Google Play Release Checklist (Store Flavor)

## Build
- Update `app/build.gradle.kts` versionCode/versionName (done: 101 / 1.0.1).
- Use `store` flavor to remove SMS permissions and components:
  - Android Studio: Build > Select build variant `storeRelease`.
  - CLI: `./gradlew bundleStoreRelease` (requires Android SDK).

## Policy & Data Safety
- Privacy policy URL: host `docs/PRIVACY_POLICY.md` and link it.
- Data Safety form: declare message content processing, local storage, no sale.
- Special accesses justification: Notification access, overlays.

## Listing Assets
- Icon 512×512, feature graphic 1024×500, screenshots (phone).
- Short & full descriptions emphasizing respectful auto‑replies and boundaries.

## Testing
- Internal testing track: upload AAB, add testers, confirm install and activation.
- Monitor crashes/ANRs; verify `/reply` works with valid license.

## Production
- Staged rollout (10–20%), monitor vitals and user feedback.

## Notes
- The `full` flavor retains SMS permissions for non‑Play distribution.
