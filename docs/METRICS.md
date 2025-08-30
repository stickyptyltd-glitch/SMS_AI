# Metrics

## Endpoints
- `GET /metrics`: Prometheus‑style text format with minimal counters.
- `GET /health`: Basic liveness (JSON).

## Exposed Metrics
- `smsai_uptime_seconds`: Process uptime in seconds.
- `smsai_requests_total{route}`: Request counts by route (`/reply`, `/assist`).
- `smsai_errors_total{route}`: Error counts by route.
- `smsai_reply_latency_seconds_sum` and `_count`: Sum and count of `/reply` latencies (compute average).

## Notes
- No external deps; suitable for lightweight scrape.
- For full Prometheus client integration, replace with `prometheus_client` and standard buckets.
