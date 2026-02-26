# SOP: Latency Spike Response

## Scope
api-gw (or other service) P99 latency above threshold (e.g. > 1000 ms).

## Procedure
1. Acknowledge within SLA (e.g. 15 min).
2. Follow **Runbook: P99 Latency Spike (api-gw)** in `knowledge/runbooks/latency_spike.md`.
3. Create or update incident; assess user impact for severity.
4. Escalate to backend owners if downstream dependency is cause.
5. Close with root cause and performance improvement actions.

## Severity
- Default: P2; P1 if SLA breach or major outage risk.
