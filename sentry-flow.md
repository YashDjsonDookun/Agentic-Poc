# SENTRY / ARGUS — Agent Flow

High-level flow: **Monitoring → Incident Handler → Doc Gen & SOP**, with micro-steps and micro-agents (human solicitation, Jira/ServiceNow, etc.).

---

## ASCII Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           SENTRY / ARGUS — HIGH-LEVEL FLOW                               │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════════════════════════════
  PHASE 1: MONITORING (Sentinel / Watchdog)
  ═══════════════════════════════════════════════════════════════════════════════════════

     [Servers] [Services] [Daemons] [Jobs] [Devices] [Metrics] [Logs] [APM]
            \      |      /     \    |    /      \     |     /    \   |   /
             \     |     /       \   |   /        \    |    /      \  |  /
              ▼    ▼    ▼         ▼  ▼  ▼          ▼   ▼   ▼        ▼ ▼ ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  COLLECT & NORMALIZE                                    [micro: Collector]    │
  │  • Scrape / poll / stream (Prometheus, Nagios, Datadog, Splunk, etc.)        │
  │  • Normalize schemas, units, timestamps                                      │
  │  • Dedupe, sample, aggregate where needed                                    │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  EVALUATE & CORRELATE                                  [micro: Evaluator]    │
  │  • Apply thresholds, SLIs, anomaly detection                                  │
  │  • Correlate across sources (e.g. log spike + CPU spike)                     │
  │  • Enrich with topology / dependency map                                      │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  DECIDE: ALERT vs IGNORE vs SUPPRESS              [micro: Alert Router]      │
  │  • Business rules, maintenance windows, on-call calendar                      │
  │  • Noise reduction, grouping of similar alerts                                │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │ (no incident)     │ (create incident) │
                    ▼                   ▼                   │
              [Log / Trend]    ┌────────────────────────────┴────────────────────┐
                               │  CREATE INCIDENT RECORD              [micro:     │
                               │  • Severity, service, env, summary   Incident    │
                               │  • Attach context (metrics, logs)    Creator]    │
                               └─────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  NOTIFY HUMANS (optional, parallel)               [micro: Notifier]          │
  │  • Email (SMTP, SendGrid…)  • Teams/Slack  • PagerDuty  • SMS  • Phone       │
  │  • Escalation policies, on-call rotation                                       │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  TICKET CREATION (optional, parallel)              [micro: Ticket Writer]     │
  │  • Jira: create issue, link to service/project, set labels, priority         │
  │  • ServiceNow: create incident, assign group, set CI, category                │
  │  • PagerDuty / Opsgenie: create event, attach context                         │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ═══════════════════════════════════════════════════════════════════════════════════════
  PHASE 2: INCIDENT HANDLING (Triage / Remediator)
  ═══════════════════════════════════════════════════════════════════════════════════════

  [New/Updated Incident] ◄──── from Monitoring or from Human (manual ticket)
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  ROOT CAUSE ANALYSIS (RCA)                         [micro: RCA Agent]         │
  │  • Query logs, traces, metrics for time window                                 │
  │  • Dependency / change correlation (deploy, config change)                    │
  │  • Hypothesis generation + ranking                                             │
  │  • Output: likely cause(s), confidence, evidence snippets                      │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  TICKET ENRICHMENT                               [micro: Enricher]            │
  │  • Add RCA summary, links to runbooks, past similar incidents                 │
  │  • Jira: update description, add labels, link related issues                  │
  │  • ServiceNow: update work notes, assignment group, knowledge links           │
  │  • Attach graphs, log excerpts, trace IDs                                      │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  RESOLUTION RECOMMENDATION                      [micro: Recommender]          │
  │  • Match to known fixes, runbooks, past resolutions                           │
  │  • Suggest steps (or parameterized playbooks)                                  │
  │  • Risk / impact note for each option                                         │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
  │ SOLICIT HUMAN       │  │ AUTO-ACTION        │  │ UPDATE TICKET       │
  │ [micro: Solicitor]  │  │ [micro: Executor]  │  │ [micro: Ticket      │
  │ • Email summary +   │  │ • Run approved     │  │       Updater]      │
  │   ask for approval  │  │   scripts/runbooks │  │ • Jira/SN: add      │
  │ • Teams/Slack:      │  │ • Rollback, scale, │  │   comment, transition│
  │   interactive card  │  │   restart, config  │  │   status             │
  │   (Approve/Reject)  │  │ • With guardrails  │  │ • PagerDuty: resolve │
  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  RESOLUTION CONFIRMATION / CLOSURE                  [micro: Closer]           │
  │  • Verify metrics/logs back to normal  • Close ticket  • Notify stakeholders  │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ═══════════════════════════════════════════════════════════════════════════════════════
  PHASE 3: DOC GEN & SOP (Chronicler)
  ═══════════════════════════════════════════════════════════════════════════════════════

  [Closed Incidents] [RCA outputs] [Actions taken] [Historical patterns]
            \              |              /                |
             \             ▼             /                 ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  AGGREGATE & CORRELATE                             [micro: Aggregator]         │
  │  • Cluster similar incidents  • Recurring themes  • Service/component hotspots│
  │  • Success/failure of past resolutions                                          │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  GENERATE / UPDATE ARTIFACTS                       [micro: Doc Writer]          │
  │  • SOPs: step-by-step for common scenarios                                       │
  │  • Tech specs: architecture, dependencies, SLIs                                │
  │  • Runbooks: when/how to execute, inputs, rollback                               │
  │  • Post-mortem drafts: timeline, cause, what we'll fix                           │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  PUBLISH & NOTIFY                                 [micro: Publisher]           │
  │  • Confluence / Wiki / Git (markdown)  • ServiceNow KB  • Internal portal      │
  │  • Notify owners: "New runbook for <service>" (email, Teams)                    │
  │  • Optional: human review workflow before publish                              │
  └──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              [Living docs feed back into
                               RCA & Recommender in Phase 2]
```

---

## Micro-agents summary

| Micro-agent | Phase | Role |
|-------------|-------|------|
| **Collector** | Monitor | Ingest and normalize from servers, services, daemons, jobs, devices, metrics, logs, APM. |
| **Evaluator** | Monitor | Thresholds, SLIs, anomaly, correlation, topology. |
| **Alert Router** | Monitor | Decide alert vs ignore/suppress; group and dedupe. |
| **Incident Creator** | Monitor | Create incident record with severity, context, links. |
| **Notifier** | Monitor | Email, Teams, Slack, PagerDuty, SMS, escalation. |
| **Ticket Writer** | Monitor | Create Jira issue / ServiceNow incident / PagerDuty event. |
| **RCA Agent** | Incident | Hypotheses, evidence, confidence. |
| **Enricher** | Incident | Enrich Jira/ServiceNow with RCA, runbooks, links. |
| **Recommender** | Incident | Suggested resolution steps / playbooks. |
| **Solicitor** | Incident | Email/Teams/Slack to solicit human approval. |
| **Executor** | Incident | Run approved actions (scripts, rollback, restart). |
| **Ticket Updater** | Incident | Update Jira/SN status, comments, PagerDuty resolve. |
| **Closer** | Incident | Verify resolution, close ticket, notify. |
| **Aggregator** | Doc/SOP | Cluster incidents, themes, hotspots. |
| **Doc Writer** | Doc/SOP | SOPs, tech specs, runbooks, post-mortem drafts. |
| **Publisher** | Doc/SOP | Confluence, ServiceNow KB, Git; notify owners. |

The **orchestrator** (SENTRY/ARGUS) sits above this flow and decides when to invoke each phase and which micro-agents to call at each step.
