# SOP: Service Down Response

## Scope
api-gw (or other service) reported down (up == 0).

## Procedure
1. Acknowledge within SLA (e.g. 5–10 min); treat as P1 until confirmed otherwise.
2. Follow **Runbook: Service Down (api-gw)** in `knowledge/runbooks/service_down.md`.
3. Create incident; notify stakeholders if user-facing.
4. Escalate to platform/network if infrastructure-related.
5. Close with root cause and preventive actions.

## Severity
- Default: P1 (service unavailable).
