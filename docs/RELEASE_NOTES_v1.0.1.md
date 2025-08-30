# Release v1.0.1

## Summary
Adds lightweight metrics and a Prometheus‑style `/metrics` endpoint for observability.

## Changes
- API: new `GET /metrics` exposition with uptime, request/error counters, and `/reply` latency sum/count.
- API: confirm `GET /health` liveness endpoint.
- Docs: added `docs/METRICS.md` with scrape details.

## Migration Steps
- None. Endpoint is additive and optional.

## Verification
- `curl http://<host>:8081/metrics` returns text; check counters increase with traffic.
- Average reply latency = `smsai_reply_latency_seconds_sum / smsai_reply_latency_seconds_count`.

## Rollback
- Re-deploy v1.0.0 if needed.
