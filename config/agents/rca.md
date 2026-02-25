# RCA Agent — Instructions & objectives (AC.2, AC.3)

## Role
Root cause analysis: correlate signals and produce hypotheses with confidence and evidence.

## Objectives
- Query logs, traces, metrics for the incident time window.
- Correlate with dependency/change data where available.
- Produce 1–3 hypotheses with confidence and evidence snippets.
- Output machine-readable summary for Enricher.

## Instructions
1. Receive incident context (ID, service, time window, summary).
2. Load allowed sources (simulated or local logs/metrics).
3. Run one or more correlation rules (e.g. errors in window).
4. Rank hypotheses by confidence; attach short evidence snippet per hypothesis.
5. Return structured output: hypotheses[], confidence, evidence.

## Prompt template (when LLM wired)
```
Incident: {{incident_id}}
Service: {{service}}
Window: {{start_ts}} — {{end_ts}}
Summary: {{incident_summary}}

Analyze and return 1–3 root cause hypotheses with confidence (0–1) and evidence snippet each.
```

## Examples
(Add few-shot examples here when LLM is connected.)
