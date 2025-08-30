# Android App Signing — Checklist

## 1) Create Keystore (once)
- keytool -genkeypair -v -keystore dayle-keystore.jks -alias dayle -keyalg RSA -keysize 4096 -validity 3650
- Store the JKS securely (not in git). Record passwords in a secret manager.

## 2) Configure Signing in Gradle (local only)
- Put credentials in `~/.gradle/gradle.properties`:
  - DAYLE_STORE_FILE=/absolute/path/dayle-keystore.jks
  - DAYLE_STORE_PASSWORD=********
  - DAYLE_KEY_ALIAS=dayle
  - DAYLE_KEY_PASSWORD=********
- In Android Studio: Build > Generate Signed Bundle/APK, select `storeRelease` or `fullRelease` and the above keystore.

## 3) Build App Bundle (AAB)
- Android Studio: Build > Generate Signed Bundle/APK > Android App Bundle > select flavor and release.
- CLI (with SDK configured): ./gradlew bundleStoreRelease or ./gradlew bundleFullRelease

## 4) Signature Schemes
- Enable v1, v2, v3 in the signing dialog (recommended). Play App Signing is also recommended.

## 5) Versioning
- app/build.gradle.kts: bump `versionCode` (int) and `versionName` for each release (current: 101 / 1.0.1).

## 6) Proguard/R8
- Release is minified with default optimize rules and `proguard-rules.pro`.
- Verify critical classes aren’t stripped (network models and UI are kept already).

## 7) Play App Signing (Recommended)
- Opt‑in in Play Console. Upload your upload‑key keystore (the JKS above). Google manages the app signing key.

## 8) Distribute
- Play (store flavor): Upload AAB to internal test > closed/open > production.
- Sideload (full flavor): Generate APK/AAB for `fullRelease` and distribute outside Play.
