# Runbook: Error Rate Spike (app-svc)

## Trigger
- Metric: `error_rate`
- Condition: value > 5% (e.g. ratio > 0.05)
- Service: app-svc

## Steps
1. **Verify** — Confirm error rate in logs and metrics (e.g. 5xx, exceptions).
2. **Logs** — Search app-svc logs for the time window; identify exception types and stack traces.
3. **Deployments** — Check for recent deployments or config changes that might have introduced the errors.
4. **Rollback** — If linked to a recent change, consider rollback after approval.
5. **Document** — Record root cause and fix in the incident.

## Contacts
- App/SRE on-call
- Dev team for code-level fixes
