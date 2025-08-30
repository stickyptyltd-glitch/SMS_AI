#!/usr/bin/env python3
"""
License Issuer (Offline, HS256)

Generates activation tokens signed with the shared issuer secret
stored at `licensing/issuer_secret.key` (base64 or raw bytes).

Usage:
  python tools/license_issuer.py \
    --license-id LIC-001 \
    --tier pro \
    --expires 2025-12-31 \
    --hardware-id ANY \
    --features core,assist \
    --max-contacts 100 --max-messages-per-day 1000
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def load_secret(path: str) -> bytes:
    with open(path, 'rb') as f:
        raw = f.read().strip()
        try:
            return base64.b64decode(raw)
        except Exception:
            return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--license-id', required=True)
    ap.add_argument('--tier', default='starter')
    ap.add_argument('--expires', required=True, help='YYYY-MM-DD')
    ap.add_argument('--hardware-id', default='ANY')
    ap.add_argument('--features', default='core')
    ap.add_argument('--max-contacts', type=int, default=10)
    ap.add_argument('--max-messages-per-day', type=int, default=100)
    ap.add_argument('--support-level', default='community')
    ap.add_argument('--issuer-secret', default=os.environ.get('LICENSE_ISSUER_SECRET') or os.path.join('licensing', 'issuer_secret.key'))
    args = ap.parse_args()

    # Build payload
    expires_iso = datetime.fromisoformat(args.expires).replace(tzinfo=timezone.utc).isoformat()
    payload = {
        'license_id': args.license_id,
        'tier': args.tier,
        'expires': expires_iso,
        'hardware_id': args.hardware_id,
        'issued': datetime.now(timezone.utc).isoformat(),
        'features': [x.strip() for x in args.features.split(',') if x.strip()],
        'max_contacts': args.max_contacts,
        'max_messages_per_day': args.max_messages_per_day,
        'support_level': args.support_level,
    }

    header = {'alg': 'HS256', 'typ': 'DAYLE-LIC'}
    header_b64 = b64url(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()

    secret = load_secret(args.issuer_secret)
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    token = f"{header_b64}.{payload_b64}.{b64url(sig)}"
    print(token)


if __name__ == '__main__':
    main()
