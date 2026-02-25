# SENTRY / ARGUS — Agentic POC

Pitch-ready MVP: monitoring → incident → ticket flow with simulator, Streamlit hub, and config-only external services.

## Setup

```bash
cd Agentic-Poc
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env     # optional: add secrets for Teams, Jira, etc.
```

## Run

**Orchestrator (FastAPI)**  
```bash
uvicorn orchestrator.main:app --reload
```
Events: `POST http://127.0.0.1:8000/events` with `{"type": "simulated", "payload": {...}}`.

**Streamlit UI**  
```bash
streamlit run ui/app.py
```
From project root so `shared`, `orchestrator`, `agents`, `integrations` are importable.

**Simulator (CLI)**  
```bash
python simulator/run.py --list
python simulator/run.py high_cpu -n 2
python simulator/run.py high_cpu --api   # POST to orchestrator
```

## Structure

- `config/` — YAML + CSV tables (agents, services, integrations, RAG placeholder).
- `data/` — Audit logs (simple/comprehensive CSV), incidents, historical.
- `knowledge/` — Runbooks, SOPs, generated (RAG sources).
- `orchestrator/` — FastAPI app, router, policy, webhooks.
- `agents/` — Monitor, notify, tickets, triage, chronicler.
- `integrations/` — ServiceNow, Jira, Teams, SMTP, Twilio (stubs when not configured).
- `teams/` — RiveScript + Adaptive Card templates.
- `simulator/` — Scenario definitions and CLI.
- `ui/` — Streamlit hub (config, tables, logs, tickets, simulate).

## Plan

See `sentry-flow.md` and `sentry-values-and-roadmap.md` for flow and roadmap. Implementation checklist is in the plan file (not in repo).
