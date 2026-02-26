"""
Insights & Dependency Graphs: visual analytics for linked tickets,
category distribution, severity trends, resolution patterns, and master/child trees.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import DATA_DIR
from shared.trace import TRACE_PATH

st.title("Insights & Dependency Graphs")
st.caption("Visual analytics: ticket relationships, category breakdowns, severity trends, and agent activity.")

incidents_path = DATA_DIR / "incidents" / "incidents.csv"

# ── Load data ─────────────────────────────────────────────────────────
df = pd.DataFrame()
if incidents_path.exists():
    df = pd.read_csv(incidents_path, dtype=str).fillna("")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ("status", "severity", "parent_incident_id", "parent_ticket_number",
                "ticket_number", "service", "summary"):
        if col not in df.columns:
            df[col] = ""

df_trace = pd.DataFrame()
if TRACE_PATH.exists():
    df_trace = pd.read_csv(TRACE_PATH, dtype=str).fillna("")

if df.empty:
    st.info("No incidents yet. Run some simulations first.")
    st.stop()

SEV_COLORS = {"critical": "#e74c3c", "high": "#e67e22", "medium": "#f1c40f", "low": "#2ecc71"}

# ═══════════════════════════════════════════════════════════════════════
# 1. Master / Child Dependency Tree
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Ticket Dependency Tree")
st.caption("Master tickets and their linked children. Shows how incidents are grouped by correlation.")

parents = df[df["parent_incident_id"] == "SELF"]
children = df[(df["parent_incident_id"] != "") & (df["parent_incident_id"] != "SELF")]

if parents.empty and children.empty:
    st.info("No parent/child relationships detected yet. Correlated incidents will appear here.")
else:
    for _, p_row in parents.iterrows():
        p_id = p_row.get("incident_id", "")
        p_ticket = p_row.get("ticket_number", "") or p_id
        p_sev = (p_row.get("severity") or "medium").lower()
        p_status = (p_row.get("status") or "open").lower()
        p_summary = p_row.get("summary", "")
        p_service = p_row.get("service", "")
        sev_c = SEV_COLORS.get(p_sev, "#95a5a6")
        stat_c = "#2ecc71" if p_status == "closed" else "#3498db"

        st.markdown(
            f'<div style="border:2px solid {sev_c};border-radius:8px;padding:12px 16px;margin-bottom:4px;'
            f'background:rgba(128,128,128,0.04);">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">'
            f'<span style="font-weight:800;font-size:1.1em;">'
            f'<span style="background:{sev_c};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.7em;'
            f'vertical-align:middle;margin-right:6px;">MASTER</span>'
            f'{p_ticket}</span>'
            f'<span>'
            f'<span style="background:{sev_c};color:#fff;padding:1px 8px;border-radius:12px;font-size:0.75em;">{p_sev}</span> '
            f'<span style="background:{stat_c};color:#fff;padding:1px 8px;border-radius:12px;font-size:0.75em;">{p_status}</span>'
            f'</span></div>'
            f'<div style="font-size:0.9em;margin-top:4px;">{p_summary}</div>'
            f'<div style="font-size:0.78em;opacity:0.55;">Service: {p_service}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        kids = children[children["parent_incident_id"] == p_id]
        if kids.empty:
            st.caption("  No child tickets linked.")
        else:
            for _, c_row in kids.iterrows():
                c_ticket = c_row.get("ticket_number", "") or c_row.get("incident_id", "")
                c_sev = (c_row.get("severity") or "").lower()
                c_status = (c_row.get("status") or "open").lower()
                c_summary = c_row.get("summary", "")
                c_sev_c = SEV_COLORS.get(c_sev, "#95a5a6")
                c_stat_c = "#2ecc71" if c_status == "closed" else "#3498db"

                st.markdown(
                    f'<div style="margin-left:32px;border-left:3px solid {c_sev_c};padding:8px 12px;'
                    f'margin-bottom:3px;border-radius:4px;background:rgba(128,128,128,0.03);">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">'
                    f'<span style="font-weight:600;">'
                    f'<span style="opacity:0.4;margin-right:4px;">&#x2514;</span>'
                    f'{c_ticket}</span>'
                    f'<span>'
                    f'<span style="background:{c_sev_c};color:#fff;padding:1px 6px;border-radius:10px;font-size:0.72em;">{c_sev}</span> '
                    f'<span style="background:{c_stat_c};color:#fff;padding:1px 6px;border-radius:10px;font-size:0.72em;">{c_status}</span>'
                    f'</span></div>'
                    f'<div style="font-size:0.85em;opacity:0.8;">{c_summary}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 2. Category Distribution
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Incidents by Category")

_theme_map = {
    "cpu": "Hardware / CPU",
    "memory": "Hardware / Memory",
    "error": "Software / Application",
    "down": "Software / Service",
    "latency": "Network / Latency",
}

def _infer_category(summary: str) -> str:
    s = summary.lower()
    for kw, cat in _theme_map.items():
        if kw in s:
            return cat
    return "Other"

df["_category"] = df["summary"].apply(_infer_category)
cat_counts = df["_category"].value_counts().reset_index()
cat_counts.columns = ["Category", "Count"]

col_chart, col_table = st.columns([3, 2])
with col_chart:
    st.bar_chart(cat_counts.set_index("Category"), height=280)
with col_table:
    st.dataframe(cat_counts, hide_index=True, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# 3. Severity Distribution (donut-style breakdown)
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Severity Breakdown")

sev_counts = df["severity"].str.lower().value_counts()
sev_order = ["critical", "high", "medium", "low"]
sev_sorted = sev_counts.reindex(sev_order).fillna(0).astype(int)

s_cols = st.columns(len(sev_order))
for i, sev in enumerate(sev_order):
    cnt = int(sev_sorted.get(sev, 0))
    color = SEV_COLORS.get(sev, "#95a5a6")
    total = len(df) or 1
    pct = round(cnt / total * 100)
    with s_cols[i]:
        st.markdown(
            f'<div style="text-align:center;padding:14px;border-radius:10px;'
            f'background:rgba(128,128,128,0.05);border-bottom:4px solid {color};">'
            f'<div style="font-size:2.2em;font-weight:800;">{cnt}</div>'
            f'<div style="font-size:0.85em;text-transform:uppercase;font-weight:600;color:{color};">{sev}</div>'
            f'<div style="font-size:0.75em;opacity:0.5;">{pct}%</div>'
            f'</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 4. Open vs Closed over Time
# ═══════════════════════════════════════════════════════════════════════
if "timestamp" in df.columns and df["timestamp"].notna().any():
    st.markdown("---")
    st.markdown("### Incident Volume Over Time")
    df_time = df.copy()
    df_time["date"] = df_time["timestamp"].dt.date
    daily = df_time.groupby(["date", "status"]).size().unstack(fill_value=0)
    st.bar_chart(daily, height=250)

# ═══════════════════════════════════════════════════════════════════════
# 5. Service Heatmap
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Incidents by Service")

svc_sev = df.groupby(["service", "severity"]).size().unstack(fill_value=0)
for sev in sev_order:
    if sev not in svc_sev.columns:
        svc_sev[sev] = 0
svc_sev = svc_sev[sev_order]
st.bar_chart(svc_sev, height=260)

# ═══════════════════════════════════════════════════════════════════════
# 6. Agent Activity (from trace)
# ═══════════════════════════════════════════════════════════════════════
if not df_trace.empty and "agent" in df_trace.columns:
    st.markdown("---")
    st.markdown("### Agent Activity")
    st.caption("How many steps each agent has executed across all pipeline runs.")

    agent_counts = df_trace[df_trace["outcome"] != "started"]["agent"].value_counts().reset_index()
    agent_counts.columns = ["Agent", "Steps"]
    st.bar_chart(agent_counts.set_index("Agent"), height=260)

# ═══════════════════════════════════════════════════════════════════════
# 7. Resolution Patterns
# ═══════════════════════════════════════════════════════════════════════
closed_df = df[df["status"].str.lower() == "closed"]
if not closed_df.empty:
    st.markdown("---")
    st.markdown("### Resolution Patterns")
    st.caption("Categories and services with the most resolved incidents.")

    res_cat = closed_df["_category"].value_counts().reset_index()
    res_cat.columns = ["Category", "Resolved"]
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**By Category**")
        st.bar_chart(res_cat.set_index("Category"), height=200)
    with col_b:
        st.markdown("**By Service**")
        res_svc = closed_df["service"].value_counts().reset_index()
        res_svc.columns = ["Service", "Resolved"]
        st.bar_chart(res_svc.set_index("Service"), height=200)

# ═══════════════════════════════════════════════════════════════════════
# 8. Correlation / Linkage Summary
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Linkage Summary")

total = len(df)
n_parents = len(parents)
n_children = len(children)
n_standalone = total - n_parents - n_children

l1, l2, l3, l4 = st.columns(4)
l1.metric("Total Incidents", total)
l2.metric("Master Tickets", n_parents)
l3.metric("Child Tickets", n_children)
l4.metric("Standalone", n_standalone)
