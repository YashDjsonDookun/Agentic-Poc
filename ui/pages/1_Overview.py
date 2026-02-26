"""
Overview dashboard: KPIs, incident breakdown, recent activity, and quick links.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import DATA_DIR
from shared.trace import TRACE_PATH

st.title("Overview")
st.caption("Dashboard — key metrics, incident status, and recent pipeline activity.")

incidents_path = DATA_DIR / "incidents" / "incidents.csv"
audit_path = DATA_DIR / "audit" / "simple.csv"

# ── Load data ─────────────────────────────────────────────────────────
df_inc = pd.DataFrame()
if incidents_path.exists():
    df_inc = pd.read_csv(incidents_path, dtype=str).fillna("")
    if "timestamp" in df_inc.columns:
        df_inc["timestamp"] = pd.to_datetime(df_inc["timestamp"], errors="coerce")
    for col in ("status", "severity", "ticket_number", "ticket_system"):
        if col not in df_inc.columns:
            df_inc[col] = "open" if col == "status" else ""

df_audit = pd.DataFrame()
if audit_path.exists():
    df_audit = pd.read_csv(audit_path, dtype=str).fillna("")
    if "timestamp" in df_audit.columns:
        df_audit["timestamp"] = pd.to_datetime(df_audit["timestamp"], errors="coerce")

df_trace = pd.DataFrame()
if TRACE_PATH.exists():
    df_trace = pd.read_csv(TRACE_PATH, dtype=str).fillna("")

# ── KPI Metrics ───────────────────────────────────────────────────────
st.markdown("### Key Metrics")
total = len(df_inc)
open_count = len(df_inc[df_inc["status"].str.lower() != "closed"]) if total else 0
closed_count = total - open_count
pipeline_runs = df_trace["run_id"].nunique() if not df_trace.empty and "run_id" in df_trace.columns else 0
audit_events = len(df_audit)

sev_counts = {}
if not df_inc.empty and "severity" in df_inc.columns:
    sev_counts = df_inc["severity"].str.lower().value_counts().to_dict()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Incidents", total)
k2.metric("Open", open_count, delta=f"-{closed_count} closed" if closed_count else None,
          delta_color="normal")
k3.metric("Pipeline Runs", pipeline_runs)
k4.metric("Audit Events", audit_events)

# ── Severity breakdown ────────────────────────────────────────────────
st.markdown("### Severity Breakdown")

SEV_ORDER = ["critical", "high", "medium", "low"]
SEV_COLORS = {"critical": "#e74c3c", "high": "#e67e22", "medium": "#f1c40f", "low": "#2ecc71"}

s_cols = st.columns(len(SEV_ORDER))
for i, sev in enumerate(SEV_ORDER):
    cnt = sev_counts.get(sev, 0)
    color = SEV_COLORS[sev]
    with s_cols[i]:
        st.markdown(
            f'<div style="text-align:center;padding:12px;border-radius:8px;'
            f'background:rgba(128,128,128,0.06);border-left:4px solid {color};">'
            f'<div style="font-size:2em;font-weight:700;">{cnt}</div>'
            f'<div style="font-size:0.85em;opacity:0.6;text-transform:uppercase;">{sev}</div>'
            f'</div>', unsafe_allow_html=True)

# ── Open vs Closed chart ─────────────────────────────────────────────
if total > 0:
    st.markdown("### Status Distribution")
    status_df = df_inc["status"].str.lower().value_counts().reset_index()
    status_df.columns = ["Status", "Count"]
    st.bar_chart(status_df.set_index("Status"), height=200)

# ── Recent incidents with quick links ─────────────────────────────────
st.markdown("---")
st.markdown("### Recent Incidents")

if df_inc.empty:
    st.info("No incidents yet. Use **Simulate issues** to create some.")
else:
    recent = df_inc.sort_values("timestamp", ascending=False).head(10)

    # Build trace lookup for workflow links
    trace_map: dict[str, str] = {}
    if not df_trace.empty and "incident_id" in df_trace.columns and "ticket_number" in df_trace.columns:
        for _, tr in df_trace.drop_duplicates("incident_id").iterrows():
            iid = tr.get("incident_id", "")
            tnum = tr.get("ticket_number", "")
            if iid:
                trace_map[iid] = tnum or iid

    for _, row in recent.iterrows():
        inc_id = row.get("incident_id", "")
        t_num = row.get("ticket_number", "") or ""
        sev = (row.get("severity", "") or "").lower()
        status = (row.get("status", "open") or "open").lower()
        summary = row.get("summary", "")
        service = row.get("service", "")
        ts = row.get("timestamp", "")
        display = t_num or inc_id

        sev_color = SEV_COLORS.get(sev, "#95a5a6")
        status_color = "#2ecc71" if status == "closed" else "#3498db"

        st.markdown(
            f'<div style="border-left:4px solid {sev_color};padding:8px 14px;margin-bottom:6px;'
            f'border-radius:6px;background:rgba(128,128,128,0.05);">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;">'
            f'<span style="font-weight:700;">{display}</span>'
            f'<span>'
            f'<span style="background:{sev_color};color:#fff;padding:1px 8px;border-radius:10px;font-size:0.75em;font-weight:600;">{sev}</span> '
            f'<span style="background:{status_color};color:#fff;padding:1px 8px;border-radius:10px;font-size:0.75em;font-weight:600;">{status}</span>'
            f'</span></div>'
            f'<div style="font-size:0.88em;margin-top:2px;">{summary}</div>'
            f'<div style="font-size:0.76em;opacity:0.5;">Service: {service} · {ts}</div>'
            f'</div>', unsafe_allow_html=True)

        btn_cols = st.columns([1, 1, 4])
        wf_key = trace_map.get(inc_id, "")
        with btn_cols[0]:
            if wf_key:
                if st.button("Workflow", key=f"ov_wf_{inc_id}"):
                    st.query_params["ticket"] = display
                    st.switch_page("pages/7_Workflow.py")
            else:
                st.caption("No trace")
        with btn_cols[1]:
            if st.button("Tickets", key=f"ov_tk_{inc_id}"):
                st.switch_page("pages/4_Tickets.py")

# ── Generate Docs (Phase 4 — Chronicler trigger) ─────────────────────
st.markdown("---")
st.markdown("### Documentation Generation")
st.caption("Generate runbook/SOP docs (.md, .docx, .pdf) from all closed incidents.")
if st.button("Generate Docs Now", key="gen_docs_btn"):
    import httpx
    base_url = "http://127.0.0.1:8000"
    try:
        r = httpx.post(f"{base_url}/generate-docs", timeout=30.0)
        if 200 <= r.status_code < 300:
            data = r.json()
            st.success(f"Generated {data.get('docs_generated', 0)} doc(s) from {data.get('clusters', 0)} cluster(s).")
        else:
            st.error(f"Doc generation failed: HTTP {r.status_code}")
    except Exception as e:
        st.error(f"Could not reach orchestrator: {e}")

# ── Recent audit activity ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### Recent Audit Activity")

if df_audit.empty:
    st.info("No audit entries yet.")
else:
    overview_sort = st.selectbox("Order", ["Newest first", "Oldest first"], key="ov_sort")
    asc = overview_sort == "Oldest first"
    if "timestamp" in df_audit.columns:
        df_audit = df_audit.sort_values("timestamp", ascending=asc)
    st.dataframe(df_audit.head(30), use_container_width=True, hide_index=True)

# ── Pipeline run summary ──────────────────────────────────────────────
if not df_trace.empty and "run_id" in df_trace.columns:
    st.markdown("---")
    st.markdown("### Recent Pipeline Runs")
    runs = (
        df_trace.groupby("run_id").agg(
            timestamp=("timestamp", "min"),
            ticket=("ticket_number", "last"),
            incident=("incident_id", "last"),
            steps=("step_order", "count"),
            result=("outcome", "last"),
        ).reset_index().sort_values("timestamp", ascending=False).head(10)
    )
    runs["display"] = runs.apply(lambda r: r["ticket"] if r["ticket"] else r["incident"], axis=1)

    for _, run in runs.iterrows():
        disp = run["display"] or run["run_id"]
        result = run["result"]
        r_color = "#2ecc71" if result in ("success", "completed") else "#e74c3c" if result == "failed" else "#3498db"

        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(
                f'<span style="font-weight:600;">{disp}</span> '
                f'<span style="font-size:0.8em;opacity:0.5;">{run["run_id"]} · {run["timestamp"]}</span> '
                f'<span style="background:{r_color};color:#fff;padding:1px 8px;border-radius:10px;'
                f'font-size:0.72em;font-weight:600;">{result}</span>',
                unsafe_allow_html=True)
        with c2:
            st.caption(f"{int(run['steps'])} steps")
        with c3:
            if st.button("View", key=f"ov_run_{run['run_id']}"):
                st.query_params["ticket"] = disp
                st.switch_page("pages/7_Workflow.py")
