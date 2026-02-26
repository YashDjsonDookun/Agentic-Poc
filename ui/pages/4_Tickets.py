"""
Tickets hub: list incidents (from local CSV); per-ticket workflow button + close action.
Master tickets are visually tagged; child tickets are indented under their parent.
Closing a master ticket cascades to all children.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import requests
from shared.config_loader import DATA_DIR, get_integration_credentials, get_env
from shared.trace import TRACE_PATH

st.title("Tickets")
st.caption("Incidents and ITSM tickets. Master tickets show linked children. Click **View Workflow** to see the full pipeline trace.")

incidents_path = DATA_DIR / "incidents" / "incidents.csv"
if not incidents_path.exists():
    st.info("No incidents yet. Use **Simulate issues** to create some.")
    st.stop()

df = pd.read_csv(incidents_path, dtype=str).fillna("")
if df.empty:
    st.info("No incidents yet.")
    st.stop()

if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp", ascending=False)

for col in ("ticket_id", "ticket_system", "ticket_number", "status",
            "parent_incident_id", "parent_ticket_number"):
    if col not in df.columns:
        df[col] = "open" if col == "status" else ""


def _ticket_url(row):
    tid = row.get("ticket_id") or ""
    system = (row.get("ticket_system") or "").strip().lower()
    if not tid or not system:
        return None
    if system == "jira":
        creds = get_integration_credentials("jira")
        base = (creds.get("base_url") or "").strip().rstrip("/")
        return f"{base}/browse/{tid}" if base else None
    if system == "servicenow":
        creds = get_integration_credentials("servicenow")
        base = (creds.get("instance_url") or "").strip().rstrip("/")
        return f"{base}/nav_to.do?uri=incident.do?sys_id={tid}" if base else None
    return None


df["ticket_link"] = df.apply(_ticket_url, axis=1)

_trace_map: dict[str, str] = {}
if TRACE_PATH.exists():
    try:
        tdf = pd.read_csv(TRACE_PATH, dtype=str, usecols=["run_id", "incident_id"]).fillna("")
        for _, trow in tdf.drop_duplicates("incident_id").iterrows():
            iid = trow["incident_id"]
            if iid:
                _trace_map[iid] = trow["run_id"]
    except Exception:
        pass

# ── Filters ───────────────────────────────────────────────────────────
col_s, col_f = st.columns([2, 1])
with col_s:
    sort_option = st.selectbox("Sort by", [
        "timestamp (newest first)", "timestamp (oldest first)",
        "severity", "service", "summary",
    ])
with col_f:
    sev_options = sorted(df["severity"].dropna().unique().tolist())
    status_filter = st.selectbox("Filter severity", ["All"] + sev_options)

if sort_option == "timestamp (oldest first)" and "timestamp" in df.columns:
    df = df.sort_values("timestamp", ascending=True)
elif sort_option == "severity" and "severity" in df.columns:
    df = df.sort_values("severity", ascending=True)
elif sort_option == "service" and "service" in df.columns:
    df = df.sort_values("service", ascending=True)
elif sort_option == "summary" and "summary" in df.columns:
    df = df.sort_values("summary", ascending=True)

if status_filter != "All":
    df = df[df["severity"] == status_filter]

SEV_COLORS = {
    "critical": "#e74c3c", "high": "#e67e22", "medium": "#f1c40f", "low": "#2ecc71",
}

ORCH_URL = (get_env("ORCHESTRATOR_BASE_URL")
            or os.environ.get("ORCHESTRATOR_BASE_URL")
            or "http://127.0.0.1:8000").rstrip("/")


def _render_ticket_card(row, indent: bool = False, key_prefix: str = ""):
    """Render a single ticket card with action buttons."""
    inc_id = row.get("incident_id", "")
    t_num = row.get("ticket_number", "") or ""
    t_sys = (row.get("ticket_system", "") or "").strip()
    severity = (row.get("severity", "") or "").lower()
    service = row.get("service", "")
    summary = row.get("summary", "")
    status = (row.get("status", "open") or "open").lower()
    ts = row.get("timestamp", "")
    link = row.get("ticket_link") or ""
    display_id = t_num or inc_id
    is_master = (row.get("parent_incident_id", "") or "").strip() == "SELF"

    sev_color = SEV_COLORS.get(severity, "#95a5a6")
    status_color = "#2ecc71" if status == "closed" else "#3498db"

    margin_left = "36px" if indent else "0"
    prefix_icon = '<span style="opacity:0.35;margin-right:4px;">&#x2514;</span>' if indent else ""
    master_badge = (
        '<span style="background:linear-gradient(135deg,#6c5ce7,#a29bfe);color:#fff;'
        'padding:2px 9px;border-radius:4px;font-size:0.7em;font-weight:700;'
        'vertical-align:middle;margin-right:6px;letter-spacing:0.5px;">MASTER</span>'
        if is_master else ""
    )
    border_width = "3px" if indent else "4px"
    border_style = f"border-left:{border_width} solid {sev_color};" if not is_master else (
        f"border:2px solid {sev_color};"
    )

    st.markdown(
        f'<div style="{border_style}padding:10px 14px;margin-bottom:4px;'
        f'border-radius:6px;background:rgba(128,128,128,0.06);margin-left:{margin_left};">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">'
        f'<span style="font-size:1.1em;font-weight:700;">'
        f'{prefix_icon}{master_badge}{display_id}</span>'
        f'<span style="display:flex;gap:6px;align-items:center;">'
        f'<span style="background:{sev_color};color:#fff;padding:2px 10px;border-radius:12px;'
        f'font-size:0.78em;font-weight:600;">{severity}</span>'
        f'<span style="background:{status_color};color:#fff;padding:2px 10px;border-radius:12px;'
        f'font-size:0.78em;font-weight:600;">{status}</span>'
        f'</span></div>'
        f'<div style="margin:4px 0;font-size:0.92em;">{summary}</div>'
        f'<div style="font-size:0.8em;opacity:0.6;">Service: {service} &middot; System: {t_sys or chr(8212)} &middot; {ts}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([1, 1, 1, 3])
    run_id = _trace_map.get(inc_id, "")

    with btn_cols[0]:
        if run_id:
            if st.button("View Workflow", key=f"wf_{key_prefix}{inc_id}"):
                st.query_params["ticket"] = display_id
                st.switch_page("pages/7_Workflow.py")
        else:
            st.caption("No trace")

    with btn_cols[1]:
        if link:
            st.link_button("Open in ITSM", link)

    with btn_cols[2]:
        if status != "closed":
            label = "Close (+ children)" if is_master else "Close"
            if st.button(label, key=f"close_{key_prefix}{inc_id}"):
                if is_master:
                    try:
                        r = requests.post(
                            f"{ORCH_URL}/incidents/{inc_id}/cascade-close", timeout=120)
                        if r.status_code == 200:
                            result = r.json()
                            closed_n = result.get("children_closed", 0)
                            st.success(f"Closed master {display_id} + {closed_n} children")
                            st.rerun()
                        else:
                            st.error(f"Failed: {r.status_code} — {r.text[:200]}")
                    except Exception as e:
                        st.error(f"Could not reach orchestrator: {e}")
                else:
                    try:
                        r = requests.post(f"{ORCH_URL}/incidents/{inc_id}/close", timeout=60)
                        if r.status_code == 200:
                            st.success(f"Closed {display_id}")
                            st.rerun()
                        else:
                            st.error(f"Failed: {r.status_code} — {r.text[:200]}")
                    except Exception as e:
                        st.error(f"Could not reach orchestrator: {e}")


# ── Build ordered display list ────────────────────────────────────────
st.markdown("---")

masters = df[df["parent_incident_id"] == "SELF"]
children_df = df[(df["parent_incident_id"] != "") & (df["parent_incident_id"] != "SELF")]
standalone = df[(df["parent_incident_id"] == "") | (~df["parent_incident_id"].isin(["SELF"]) &
               ~df["incident_id"].isin(children_df["incident_id"]))]
standalone = standalone[standalone["parent_incident_id"] != "SELF"]
standalone = standalone[~standalone["incident_id"].isin(children_df["incident_id"])]

rendered_ids = set()

for _, m_row in masters.iterrows():
    _render_ticket_card(m_row, indent=False, key_prefix="m_")
    rendered_ids.add(m_row["incident_id"])

    m_id = m_row["incident_id"]
    kids = children_df[children_df["parent_incident_id"] == m_id]
    for _, c_row in kids.iterrows():
        _render_ticket_card(c_row, indent=True, key_prefix="c_")
        rendered_ids.add(c_row["incident_id"])

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

remaining = df[~df["incident_id"].isin(rendered_ids)]
for _, row in remaining.iterrows():
    _render_ticket_card(row, indent=False, key_prefix="s_")

# ── Full table (collapsible) ─────────────────────────────────────────
with st.expander("Raw incidents table"):
    show_cols = [c for c in df.columns if c != "ticket_link"]
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
