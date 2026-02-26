# SOP: High CPU Response

## Scope
App-svc high CPU alerts (e.g. cpu_percent > 90%).

## Procedure
1. Acknowledge alert within SLA (e.g. 15 min).
2. Follow **Runbook: High CPU (app-svc)** in `knowledge/runbooks/high_cpu.md`.
3. Create or update incident with severity (e.g. P2/P3), assignee, and summary.
4. Escalate to app owner if not resolved within threshold (e.g. 1 hour).
5. Close incident with resolution notes and any post-mortem link.

## Severity
- Default: P2 (degraded performance); escalate to P1 if user-facing SLA at risk.
