# SENTRY/ARGUS Agentic POC — Status Report

## Project Overview

An **agentic incident management system** that automates: monitoring alerts → incident creation → triage (RCA + enrichment) → human approval → doc generation. Built with **FastAPI** (orchestrator), **Streamlit** (UI), and file-based CSV storage.

---

## What's Done (by roadmap phase)

### Phase 0: Foundation — COMPLETE

- Agent identities defined in `config/agents.yaml` (sentinel, triage, chronicler, conductor)
- Orchestrator shell (`orchestrator/main.py`) — FastAPI app with event routing
- Shared schemas (`shared/schema.py`) — `MonitoringEvent`, `Incident`, `AuditEntry`
- Config loader (`shared/config_loader.py`) — YAML + CSV config, local integration credentials
- Simulator as data source (`simulator/scenarios.py`) — 5 scenarios (high_cpu, service_down, error_spike, high_memory, latency_spike)

### Phase 1: Monitoring → Incident Creation — COMPLETE

- **Collector** (`agents/monitor/collector.py`) — normalizes payloads to `MonitoringEvent`
- **Evaluator** (`agents/monitor/evaluator.py`) — threshold rules from `config/tables/alert_rules.csv`
- **Alert Router** (`agents/monitor/alert_router.py`) — maintenance window, dedup, re-open detection
- **Incident Creator** (`agents/monitor/incident_creator.py`) — severity inference, CSV persistence
- **Correlator** (`agents/monitor/correlator.py`) — groups similar open incidents under a parent/master ticket in ServiceNow
- **Notifier** (`agents/notify/notifier.py`) — Teams webhook or email fallback
- **Ticket Writer** (`agents/tickets/ticket_writer.py`) — creates ServiceNow or Jira tickets with category/subcategory/assignment group routing from CSV lookup tables

### Phase 2: Incident Handling (Triage) — COMPLETE

- **RCA Agent** (`agents/triage/rca.py`) — rule-based hypothesis generation (5 metric templates, no LLM yet)
- **Recommender** (`agents/triage/recommender.py`) — keyword matching against `knowledge/runbooks/`, `knowledge/sops/`, `knowledge/generated/`
- **Enricher** (`agents/triage/enricher.py`) — appends RCA + runbook suggestions as work notes on ServiceNow/Jira tickets

### Phase 3: Human in the Loop & Closure — COMPLETE

- **Solicitor** (`agents/triage/solicitor.py`) — sends approval request via Teams or email
- **Executor** (`agents/triage/executor.py`) — **simulated only** (logs "simulated execution", no real server actions)
- **Ticket Updater** (`agents/tickets/ticket_updater.py`) — adds comments on approval/execution
- **Closer** (`agents/triage/closer.py`) — resolves + stops SLA + closes on ServiceNow; Jira transition stubbed
- **Approval webhook** (`orchestrator/webhooks.py`) — Approve/Reject flow with `data/approvals.csv`
- **Cascade close** — closes master ticket + all children

### Phase 4: Doc Gen & SOP (Chronicler) — COMPLETE

- **Aggregator** (`agents/chronicler/aggregator.py`) — clusters closed incidents by service + theme
- **Doc Writer** (`agents/chronicler/doc_writer.py`) — generates **.md, .docx, .pdf** from incident clusters + trace data
- **Publisher** (`agents/chronicler/publisher.py`) — writes to `knowledge/generated/` and optionally notifies via Teams
- Auto-triggered on incident close; also available via `POST /generate-docs`
- 5 generated docs already exist in `knowledge/generated/`

### Phase 5: Orchestrator Intelligence — PARTIAL

- **Policy engine** (`orchestrator/policy.py`) — route_phase, should_solicit, should_trigger_chronicler, polling toggle
- **Audit logging** (`shared/audit.py`) — simple + comprehensive CSV audit trails
- **Pipeline trace** (`shared/trace.py`) — step-by-step trace with agent/action/decision/rationale/outcome
- Config tables: `alert_rules.csv`, `severity_priority.csv`, `category_mapping.csv`, `assignment_routing.csv`, `maintenance_windows.csv`, `services.csv`

### UI (Streamlit) — BUILT

- Multi-page app with 8 pages: Overview, Configuration, Tables, Tickets, Simulate, Logs, Workflow, Insights

### Integrations — BUILT

- **ServiceNow** — fully functional (create, update work notes, close with SLA stop, resolve, group resolution)
- **Teams** — webhook messaging works
- **Jira** — create_issue works; `add_comment` and `transition` are **TODO stubs**
- **SMTP** — stub (`send_email` returns False, `# TODO: aiosmtplib`)
- **Twilio** — stub (`send_sms` returns False, `# TODO: httpx to Twilio API`)

### Knowledge Base — BUILT

- 5 hand-written runbooks in `knowledge/runbooks/` (high_cpu, high_memory, service_down, error_spike, latency_spike)
- 5 hand-written SOPs in `knowledge/sops/`
- 5 auto-generated docs in `knowledge/generated/` (.md, .docx, .pdf)

---

## What's Left / Incomplete / Good to have but also not critical for a PoC

| # | Task | Effort | Description |
|---|------|--------|-------------|
| **1** | **Jira `add_comment` + `transition`** | Small | `integrations/jira.py` lines 105–116: both methods are stubs with `# TODO`. Need actual REST calls to `/rest/api/3/issue/{key}/comment` and `/rest/api/3/issue/{key}/transitions`. |
| **2** | **SMTP integration** | Small | `integrations/smtp.py`: `send_email` is a stub. Needs `aiosmtplib` or similar wired up with credentials from config. |
| **3** | **Twilio SMS integration** | Small | `integrations/twilio.py`: `send_sms` is a stub. Needs httpx calls to Twilio API. |
| **4** | **LLM client** | Medium | `shared/llm_client.py`: `complete()` is a no-op returning `None`. When an LLM endpoint is configured (via `rag.yaml` or `.env`), this should call the actual LLM. RCA and Doc Writer could use it for richer output. |
| **5** | **LLM-powered RCA** | Medium | `agents/triage/rca.py`: currently rule-based templates only. Needs LLM integration for real hypothesis generation from logs/metrics. The `config/agents/rca.md` prompt is ready. |
| **6** | **RAG / Vector Search** | Medium–Large | `config/rag.yaml` is disabled placeholder. No vector store, no embedding pipeline, no semantic search over runbooks/SOPs. The Recommender currently does keyword matching only. |
| **7** | **Real Executor actions** | Medium | `agents/triage/executor.py`: returns simulated result. Needs actual execution capability (restart service, run playbook, etc.) with guardrails. |
| **8** | **Teams Adaptive Cards** | Small–Medium | `teams/cards/notification.json` and `teams/cards/approval.json` templates exist but the Teams integration only sends plain text via webhook. The Solicitor should send proper Adaptive Cards with Approve/Reject buttons. The `teams/rivescript/approval_flow.rive` is also unused. |
| **9** | **Second monitoring source** | Medium | Phase 5.2 from roadmap: only the simulator exists as a data source. Need real integration with Prometheus, Datadog, or similar. |
| **10** | **Escalation policies** | Medium | Notifier sends one notification. No multi-tier on-call, escalation timers, or SLA tracking (beyond the basic SNOW SLA stop). |
| **11** | **Confluence / ServiceNow KB publishing** | Small–Medium | Publisher only writes to local `knowledge/generated/`. The roadmap calls for publishing to Confluence, ServiceNow KB, or Git. |
| **12** | **Tests** | Medium | **Zero test files** exist in the project. Unit tests and integration tests are needed for all agents, orchestrator, and integrations. |
| **13** | **Database migration** | Large | Everything is CSV-based (incidents, audit, trace, approvals). For production, this needs a proper DB (SQLite minimum, Postgres for scale). |
| **14** | **Ingest webhook** | Small | `orchestrator/webhooks.py` `/webhooks/ingest` endpoint is a placeholder — accepts JSON but doesn't process it. |
| **15** | **Teams callback webhook** | Small | `orchestrator/webhooks.py` `/webhooks/teams/callback` is a placeholder — accepts POST but does nothing with it. |

---

## Suggested Task Distribution

### Quick wins (1–2 days each, 1 dev)

- **Tasks 1, 2, 3** (Jira stubs, SMTP, Twilio) — assign to one dev
- **Task 8** (Teams Adaptive Cards) — assign to one dev
- **Tasks 14, 15** (webhook placeholders) — small, can pair with any of the above

### Medium effort (3–5 days each)

- **Tasks 4 + 5** (LLM client + LLM-powered RCA) — assign together to one dev
- **Task 6** (RAG / vector search) — assign to one dev with ML/embedding experience
- **Task 7** (Real Executor) — needs careful design around safety/guardrails
- **Task 10** (Escalation policies) — one dev

### Larger initiatives

- **Task 12** (Tests) — can be spread across all devs
- **Task 13** (DB migration) — one dev, touches all modules
- **Task 9** (Real monitoring source) — depends on what monitoring tool your org uses
