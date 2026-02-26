# Runbook: High CPU (app-svc)

## Trigger
- Metric: `cpu_percent`
- Condition: value > 90%
- Service: app-svc

## Steps
1. **Verify** — Confirm CPU spike in monitoring (e.g. Grafana/Prometheus).
2. **Identify top consumers** — Run `top` or equivalent on app-svc hosts; check for runaway processes or threads.
3. **Scale / throttle** — If load is legitimate, consider horizontal scaling or request throttling.
4. **Restart if needed** — Restart affected pods/containers only after capturing thread dumps or profiles.
5. **Document** — Log actions and outcome in the incident ticket.

## Contacts
- Platform / SRE on-call
- App owner (see service registry)
