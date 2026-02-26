# Runbook: High Memory (app-svc)

## Trigger
- Metric: `memory_percent`
- Condition: value > 90%
- Service: app-svc

## Steps
1. **Verify** — Confirm memory usage in monitoring and on host/container.
2. **Heap / process** — Capture heap dump or process memory map if safe; analyze for leaks.
3. **Scale / limit** — Increase memory limits or scale out if workload is legitimate; otherwise fix leaks.
4. **Restart** — Restart affected instances if needed after capturing diagnostics.
5. **Document** — Log findings and remediation in the incident.

## Contacts
- Platform / SRE on-call
- App owner for code-level memory fixes
