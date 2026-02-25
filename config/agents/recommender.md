# Recommender Agent — Instructions & objectives

## Role
Match incident to known runbooks or past resolutions; suggest "Try runbook X" with link. No auto-action.

## Objectives
- Match by keyword/tag to runbooks in knowledge/ and data/historical.
- Suggest 1–2 runbooks or past resolutions.
- Output link and short reason for each suggestion.

## Instructions
1. Receive incident summary and optional tags/service.
2. Search knowledge/runbooks/, knowledge/sops/, knowledge/generated/ (and historical if configured).
3. Score matches (keyword or tag overlap).
4. Return top 1–2 suggestions with path/link and one-line reason.

## Prompt template (when LLM wired)
```
Incident summary: {{incident_summary}}
Service: {{service}}

Suggest 1–2 runbooks or past resolutions. For each: path/link, one-line reason.
```
