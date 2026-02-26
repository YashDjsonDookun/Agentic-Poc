# SOP: Error Rate Spike Response

## Scope
App-svc (or other service) error rate above threshold (e.g. > 5%).

## Procedure
1. Acknowledge within SLA (e.g. 15 min).
2. Follow **Runbook: Error Rate Spike (app-svc)** in `knowledge/runbooks/error_spike.md`.
3. Create or link incident; set severity based on user impact.
4. Coordinate with dev if code rollback or fix is required.
5. Close with root cause and link to change or fix.

## Severity
- Default: P2; P1 if widespread user impact or data risk.
