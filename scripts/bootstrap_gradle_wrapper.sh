#!/usr/bin/env bash
set -euo pipefail

# Bootstraps Gradle Wrapper files locally if you have Gradle installed.
# Usage: scripts/bootstrap_gradle_wrapper.sh [GRADLE_VERSION]

VERSION="${1:-8.7}"

if ! command -v gradle >/dev/null 2>&1; then
  echo "Gradle is not installed. Install Gradle or use Android Studio to generate the wrapper." >&2
  exit 1
fi

echo "Initializing Gradle wrapper (version ${VERSION})..."
gradle wrapper --gradle-version "${VERSION}" --distribution-type bin
echo "Done. You can now run ./gradlew tasks"

