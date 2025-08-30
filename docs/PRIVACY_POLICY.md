# Privacy Policy — DayleSMS AI

Effective: 2025-08-29

- Controller: st1cky.pty.ltd (Dayle LeCheyne Stueven)
- Contact: support@your-domain.example

## Data We Process
- Message content: used to generate auto‑replies and maintain lightweight memory. Stored locally in `dayle_data/` on the server.
- Identifiers: contact names or phone digits provided by you.
- Telemetry: minimal app logs; metrics counters (no PII) if `/metrics` is enabled.

## Purpose
- Provide respectful, concise auto‑replies; propose next steps; maintain recent context.

## Sharing
- No sale of data. Optional integrations (Twilio/Messenger) send message content to those providers per your configuration.

## Security
- HTTPS recommended for all endpoints; license data encrypted on disk; request timeouts; signature verification for Messenger.

## Retention
- Conversation memory persists on the server until deleted; you can purge per contact via API or app.

## Your Controls
- Purge memory via API/app; configure banned words and preferred phrases; disable automation per contact.

## Changes
- We may update this policy; we will version changes in the repository.
