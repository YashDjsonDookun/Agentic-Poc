"""
Chronicler pipeline: Aggregator -> Doc Writer -> Publisher.
Called after incident closure (auto or manual) and via the doc-gen API endpoint.
"""
from __future__ import annotations

import uuid

from shared.trace import log_step, get_run_id_for_incident, get_max_step
from agents.chronicler.aggregator import (
    cluster_incidents,
    get_closed_incidents,
    get_trace_data_for_incidents,
)
from agents.chronicler.doc_writer import generate_docs
from agents.chronicler.publisher import publish


def _run_id() -> str:
    return f"doc_{uuid.uuid4().hex[:10]}"


async def run_chronicler(
    incident_id: str = "",
    ticket_number: str = "",
) -> dict:
    """Run the full Chronicler pipeline for closed incidents.
    If incident_id is given, uses its run_id so trace appends to the existing workflow."""
    run_id = ""
    step = 1
    if incident_id:
        run_id = get_run_id_for_incident(incident_id)
        step = get_max_step(run_id) + 1 if run_id else 1
    if not run_id:
        run_id = _run_id()

    t_num = ticket_number

    # --- Aggregator ---
    log_step(run_id, incident_id, step, "Aggregator", "cluster_closed",
             "invoke", "Scanning closed incidents and clustering by service + theme.",
             "started", ticket_number=t_num)

    closed = get_closed_incidents()
    clusters = cluster_incidents(closed)
    cluster_summary = ", ".join(f"{c['cluster_key']}({c['count']})" for c in clusters[:5])

    log_step(run_id, incident_id, step, "Aggregator", "cluster_closed",
             f"{len(clusters)} clusters",
             f"Found {len(closed)} closed incidents in {len(clusters)} cluster(s): {cluster_summary}",
             "success", f"clusters={len(clusters)}", ticket_number=t_num)
    step += 1

    if not clusters:
        log_step(run_id, incident_id, step, "Pipeline", "chronicler_complete",
                 "no_data", "No closed incidents to generate docs from.",
                 "completed", ticket_number=t_num)
        return {"clusters": 0, "docs_generated": 0}

    docs_generated = 0
    all_paths: list[str] = []

    for cluster in clusters:
        inc_ids = [i.get("incident_id", "") for i in cluster.get("incidents", [])]
        trace_rows = get_trace_data_for_incidents(inc_ids)

        # --- Doc Writer ---
        log_step(run_id, incident_id, step, "Doc Writer", "generate_docs",
                 "invoke",
                 f"Generating .md, .docx, .pdf for cluster '{cluster['cluster_key']}' "
                 f"({cluster['count']} incidents).",
                 "started", ticket_number=t_num)

        paths = generate_docs(cluster, trace_rows)
        fmts = ", ".join(paths.keys())

        log_step(run_id, incident_id, step, "Doc Writer", "generate_docs",
                 f"{len(paths)} formats",
                 f"Generated {fmts} for {cluster['cluster_key']}.",
                 "success", f"files={fmts}", ticket_number=t_num)
        step += 1

        # --- Publisher ---
        log_step(run_id, incident_id, step, "Publisher", "publish_docs",
                 "invoke",
                 f"Publishing docs to knowledge/generated/ and sending optional notification.",
                 "started", ticket_number=t_num)

        result = await publish(paths, cluster_key=cluster["cluster_key"])
        notified = result.get("notified", False)

        log_step(run_id, incident_id, step, "Publisher", "publish_docs",
                 "published",
                 f"Published {len(result.get('published', []))} file(s). "
                 f"Teams notify: {'sent' if notified else 'skipped'}.",
                 "success", ticket_number=t_num)
        step += 1

        docs_generated += len(paths)
        all_paths.extend(result.get("published", []))

    log_step(run_id, incident_id, step, "Pipeline", "chronicler_complete",
             "completed",
             f"Chronicler pipeline finished: {len(clusters)} cluster(s), {docs_generated} doc(s) generated.",
             "completed", ticket_number=t_num)

    return {
        "clusters": len(clusters),
        "docs_generated": docs_generated,
        "files": all_paths,
        "run_id": run_id,
    }
