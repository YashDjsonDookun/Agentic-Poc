# SOP: High Memory Response

## Scope
App-svc (or other service) memory usage above threshold (e.g. > 90%).

## Procedure
1. Acknowledge within SLA (e.g. 15 min).
2. Follow **Runbook: High Memory (app-svc)** in `knowledge/runbooks/high_memory.md`.
3. Create or update incident; capture heap/dump if policy allows.
4. Escalate to app owner for suspected memory leaks.
5. Close with resolution and any follow-up (e.g. ticket for leak fix).

## Severity
- Default: P2; P1 if OOM kills or cascading failures.
