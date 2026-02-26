# Runbook: P99 Latency Spike (api-gw)

## Trigger
- Metric: `latency_p99_ms`
- Condition: value above threshold (e.g. > 1000 ms)
- Service: api-gw

## Steps
1. **Verify** — Confirm P99 latency in APM or metrics for api-gw and downstream.
2. **Downstream** — Check latency of app-svc and other backends; identify slow dependency.
3. **Resources** — Check CPU/memory/network on api-gw and downstream; rule out saturation.
4. **Traffic** — Consider traffic spike or bad client behavior; apply rate limits if needed.
5. **Document** — Record root cause and mitigation in the incident.

## Contacts
- API/platform on-call
- Backend service owners for slow dependencies
