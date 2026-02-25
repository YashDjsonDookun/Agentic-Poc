# SENTRY / ARGUS — Values & Implementation Roadmap

## 1. Professional & business values

| Value | What it means for the system |
|-------|-----------------------------|
| **Efficiency** | Less manual triage, fewer repeated steps, faster path from alert → RCA → resolution. Same headcount handles more incidents or more complexity. |
| **Cost** | Lower MTTR → less downtime and lost revenue. Fewer escalations and after-hours pages. Automation of repetitive work reduces labor cost per incident. |
| **Scalability** | Monitoring and response scale with systems and services without linear growth in ops headcount. |
| **Consistency** | Same process every time: thresholds, routing, enrichment, documentation. Fewer "it depends on who's on call" outcomes. |
| **Auditability** | Clear attribution (which agent did what), logs, and paper trail for compliance, post-mortems, and improvement. |
| **Reliability** | Fewer missed alerts, fewer forgotten follow-ups, runbooks and SOPs that are kept up to date by the doc agent. |
| **Time-to-value** | New services get monitoring, incident handling, and docs without reinventing the wheel each time. |

---

## 2. Holistic & organizational values

| Value | What it means for the system |
|-------|-----------------------------|
| **Human focus** | Engineers spend time on design and hard problems; agents handle repetitive, noisy, and clerical work. Solicitor and approval flows keep humans in the loop where it matters. |
| **Learning organization** | Chronicler turns incidents into SOPs and runbooks; the system gets better over time and knowledge isn't locked in individuals. |
| **Transparency** | Non-human identities and clear flows make it obvious what is automated vs human-decided. Easier trust and governance. |
| **Resilience** | Less dependence on specific people; playbooks and docs survive turnover. Correlation and history help when experts aren't available. |
| **Fairness / equity** | On-call load and escalation are rule-based; reduced bias from "who you know" or inconsistent handling. |
| **Sustainability** | Fewer fire drills and reactive heroics; more predictable work and better balance for teams. |
| **Accountability** | Clear ownership (services, runbooks, escalation) and a single place (orchestrator + agents) where "who decided what" is recorded. |

---

## 3. One-line pitch

- **Professional:** *"Lower cost and risk, higher efficiency and consistency, at scale."*
- **Holistic:** *"Better outcomes for systems and for people: less toil, more learning, clearer accountability."*

---

# Implementation roadmap (POC → MVP)

Priority order for building SENTRY/ARGUS piece by piece. Each phase delivers something demonstrable and builds on the previous one.

---

## Phase 0: Foundation (weeks 1–2)

**Goal:** Identity, plumbing, and one concrete data source.

| # | Deliverable | Description |
|---|-------------|-------------|
| 0.1 | **Non-human identity & config** | Define agent identities (e.g. `sentinel`, `triage`, `chronicler`, `conductor`), env vars, and a minimal config (e.g. one service to monitor, one alert rule). |
| 0.2 | **Orchestrator shell** | Single entry point (API or message consumer) that receives events and routes them. No real logic yet—just "received event, would route to X" logging. |
| 0.3 | **One monitoring data source** | Integrate one source (e.g. Prometheus, Datadog, or a simple health-check script). Normalize to a single internal event schema. |

**Outcome:** Events flow from one source into the orchestrator; you can show "SENTRY received an alert."

---

## Phase 1: Monitoring → incident creation (weeks 3–4)

**Goal:** Alerts become incidents; optional human notification and one ticket system.

| # | Deliverable | Description |
|---|-------------|-------------|
| 1.1 | **Collector + Evaluator (minimal)** | Ingest from Phase 0 source; apply one or two threshold rules. Output: "alert" or "no alert." |
| 1.2 | **Alert Router** | Simple rules: maintenance window, dedupe by service+metric. Decision: create incident or ignore. |
| 1.3 | **Incident Creator** | Create incident record (ID, severity, service, summary, timestamp). Store in DB or queue (e.g. SQLite, Redis, or cloud queue). |
| 1.4 | **Notifier (one channel)** | On new incident, send one notification (e.g. email or Teams). No escalation yet. |
| 1.5 | **Ticket Writer (one system)** | Create one ticket per incident in one system (Jira **or** ServiceNow). Map severity → priority, attach link back to incident. |

**Outcome:** End-to-end from metric/health → alert → incident → notification + ticket. Core monitoring value.

---

## Phase 2: Incident handling — RCA & enrichment (weeks 5–6)

**Goal:** When an incident exists, add RCA and enrich the ticket.

| # | Deliverable | Description |
|---|-------------|-------------|
| 2.1 | **Trigger from orchestrator** | Orchestrator sees new/updated incident and invokes "Triage" (incident-handler agent). |
| 2.2 | **RCA Agent (narrow scope)** | For a fixed set of sources (e.g. logs + one metric), run one correlation (e.g. "errors in window X"). Output: 1–3 hypotheses + confidence + evidence snippet. |
| 2.3 | **Enricher** | Take RCA output and update the existing ticket (Jira/ServiceNow): add description/notes, link to runbook if match exists, attach log/metric snippet. |
| 2.4 | **Recommender (simple)** | Match incident to 1–2 known runbooks or past resolutions (keyword/tag match). Suggest "Try runbook X" with link. No auto-action. |

**Outcome:** Every new incident gets RCA + enriched ticket + resolution suggestion. Demonstrates "intelligent" handling.

---

## Phase 3: Human in the loop & closure (weeks 7–8)

**Goal:** Humans can approve actions; incidents can be closed with verification.

| # | Deliverable | Description |
|---|-------------|-------------|
| 3.1 | **Solicitor** | When Recommender suggests an action, send approval request (email or Teams) with Approve/Reject. Store decision. |
| 3.2 | **Executor (one safe action)** | One approved action type (e.g. "restart service" or "run playbook X"). Execute only after approval; log outcome. |
| 3.3 | **Ticket Updater** | On approval/execution, add comment to Jira/ServiceNow; optionally transition status (e.g. In Progress → Resolved). |
| 3.4 | **Closer** | When metrics/logs indicate "healthy" again (or human marks resolved), close incident, update ticket, optionally notify "Resolved." |

**Outcome:** Full incident loop: create → analyze → recommend → approve → act → close. MVP incident handling complete.

---

## Phase 4: Doc gen & SOP (weeks 9–10)

**Goal:** Closed incidents feed documentation; first runbooks/SOPs generated.

| # | Deliverable | Description |
|---|-------------|-------------|
| 4.1 | **Aggregator** | On incident close, push event to Chronicler. Batch closed incidents; simple clustering (e.g. by service + error type). |
| 4.2 | **Doc Writer** | From 1–3 closed incidents, generate one runbook or SOP (markdown): steps, conditions, rollback. Use templates + LLM or rules. |
| 4.3 | **Publisher (one destination)** | Publish to one place (e.g. Confluence, Git repo, or ServiceNow KB). Optional: "New runbook for X" email/Teams. |
| 4.4 | **Feedback loop** | Recommender (Phase 2) can suggest the newly published runbooks for future incidents. |

**Outcome:** System that learns: incidents → docs → better recommendations. Chronicler value demonstrated.

---

## Phase 5: Orchestrator intelligence & scale (weeks 11–12)

**Goal:** Orchestrator owns "when to do what"; add more micro-agents and sources.

| # | Deliverable | Description |
|---|-------------|-------------|
| 5.1 | **Orchestrator policy** | Explicit rules: when to create incident, when to call Triage, when to call Chronicler (e.g. on close, or nightly batch). |
| 5.2 | **Second monitoring source** | Add another data source (e.g. second service, or logs). Reuse Collector/Evaluator pattern. |
| 5.3 | **Second notification/ticket channel** | Add second channel (e.g. Slack if you had Teams, or second Jira project). Reuse Notifier/Ticket Writer pattern. |
| 5.4 | **Audit & identity** | All actions stamped with agent identity and timestamp. Simple audit log (who created/updated what, when). |

**Outcome:** Multi-source, multi-channel POC with clear orchestration and audit. Ready to present as MVP.

---

## Phase 6: Post-MVP (backlog)

- **More micro-agents:** Dedicated RCA vs Enricher vs Recommender tuning; separate Executor for different action types.
- **Richer RCA:** More data sources, dependency graph, change correlation.
- **Full escalation:** Multi-tier on-call, escalation timers, SLA tracking.
- **Doc quality:** Human review workflow, versioning, feedback ("this runbook helped").
- **Dashboard:** Visibility into incidents, agent actions, and doc coverage.

---

## Summary: priority order for POC/MVP

| Priority | Focus | Phases |
|----------|--------|--------|
| **P0** | Monitoring → incident → one notification + one ticket | 0, 1 |
| **P1** | Incident handling: RCA, enrichment, recommendation | 2 |
| **P2** | Human approval + one safe action + close | 3 |
| **P3** | Doc gen: aggregate → write → publish + feedback | 4 |
| **P4** | Orchestrator policy, second source/channel, audit | 5 |

**POC** = Phases 0–2 (alert to enriched incident).  
**MVP** = Phases 0–5 (full loop: monitor → handle → document, with orchestrator and audit).
