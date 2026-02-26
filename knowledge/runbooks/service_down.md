# Runbook: Service Down (api-gw)

## Trigger
- Metric: `up`
- Condition: value == 0 (service unreachable)
- Service: api-gw

## Steps
1. **Verify** — Check health endpoint and load balancer status for api-gw.
2. **Pods / nodes** — Confirm if pods are Running and nodes are Ready (Kubernetes) or equivalent.
3. **Restart** — Restart api-gw deployment/process; verify startup logs for errors.
4. **Dependencies** — Ensure downstream services (e.g. app-svc) and DBs are reachable.
5. **Document** — Update incident with root cause and remediation.

## Contacts
- API/platform on-call
- Network/load balancer team if LB-related
