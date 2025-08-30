#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   LICENSE_ISSUER_SECRET=<base64> scripts/issue_license.sh \
#     --license-id LIC-123 --tier pro --expires 2026-12-31 \
#     --hardware-id ANY --features core,assist \
#     --max-contacts 100 --max-messages-per-day 1000

if [[ -z "${LICENSE_ISSUER_SECRET:-}" ]]; then
  echo "ERROR: LICENSE_ISSUER_SECRET env var (base64) is required" >&2
  exit 1
fi

IMG=smsai-license-issuer:latest
if ! docker image inspect "$IMG" >/dev/null 2>&1; then
  docker build -t "$IMG" docker/license-issuer
fi

docker run --rm \
  -e LICENSE_ISSUER_SECRET="$LICENSE_ISSUER_SECRET" \
  "$IMG" "$@"

