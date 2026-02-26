"""
Workflow — real-time pipeline trace for a single ticket / incident.
Split layout: left = compact flow nodes, right = expanded detail for selected step.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.trace import TRACE_PATH

# ── CSS ───────────────────────────────────────────────────────────────
st.markdown("""<style>
/* ── Flow node (left column) ── */
.fn {border-radius:8px;padding:10px 14px;margin-bottom:2px;cursor:pointer;transition:background 0.15s;}
.fn:hover {filter:brightness(1.1);}
.fn-success,.fn-completed {border-left:4px solid #2ecc71;background:rgba(46,204,113,0.09);}
.fn-failed   {border-left:4px solid #e74c3c;background:rgba(231,76,60,0.09);}
.fn-skipped  {border-left:4px solid #95a5a6;background:rgba(149,165,166,0.09);}
.fn-suppressed{border-left:4px solid #f39c12;background:rgba(243,156,18,0.09);}
.fn-default  {border-left:4px solid #3498db;background:rgba(52,152,219,0.09);}
.fn-selected {outline:2px solid #fff;outline-offset:-2px;filter:brightness(1.15);}
.fn-head {display:flex;justify-content:space-between;align-items:center;}
.fn-agent {font-size:1.05em;font-weight:700;}
.fn-ts {font-size:0.72em;opacity:0.45;}
.fn-decision {font-size:0.85em;opacity:0.75;margin-top:2px;}
.fn-badge {display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.72em;font-weight:600;color:#fff;margin-left:6px;}
.fn-badge-success,.fn-badge-completed{background:#2ecc71;}
.fn-badge-failed{background:#e74c3c;}
.fn-badge-skipped{background:#95a5a6;}
.fn-badge-suppressed{background:#f39c12;}
.fn-badge-default{background:#3498db;}
/* ── Arrow ── */
.fn-arrow {text-align:center;font-size:1.1em;opacity:0.25;margin:-1px 0;line-height:1;}
/* ── Detail panel (right column) ── */
.dp {border-radius:10px;padding:18px 20px;background:rgba(128,128,128,0.06);min-height:200px;}
.dp-title {font-size:1.2em;font-weight:700;margin-bottom:10px;}
.dp-field {margin-bottom:8px;}
.dp-label {font-size:0.82em;font-weight:600;opacity:0.55;text-transform:uppercase;letter-spacing:0.5px;}
.dp-val {font-size:0.95em;margin-top:2px;}
.dp-rationale {font-size:0.95em;padding:10px 14px;border-radius:8px;background:rgba(128,128,128,0.08);margin-top:6px;line-height:1.5;}
/* ── Info bar ── */
.wf-bar {display:flex;gap:16px;flex-wrap:wrap;align-items:center;font-size:0.92em;padding:4px 0 10px 0;}
.wf-bar code {padding:2px 6px;border-radius:4px;background:rgba(128,128,128,0.12);}
/* ── Phase separator ── */
.phase-sep {text-align:center;font-size:0.78em;font-weight:600;opacity:0.4;text-transform:uppercase;
            letter-spacing:1px;padding:4px 0;margin:4px 0;border-top:1px dashed rgba(128,128,128,0.2);}
</style>""", unsafe_allow_html=True)


def _load() -> pd.DataFrame:
    if not TRACE_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(TRACE_PATH, dtype=str).fillna("")


ICONS = {
    "Collector": "📥", "Evaluator": "📊", "Alert Router": "🚦",
    "Incident Creator": "🆕", "Notifier": "📢", "Ticket Writer": "🎫",
    "RCA Agent": "🔍", "Recommender": "📚", "Enricher": "✏️",
    "Solicitor": "🤝", "Executor": "⚙️", "Ticket Updater": "🔄",
    "Closer": "🔒", "Pipeline": "🏁",
}
PHASES = {
    "Collector": "Phase 1 — Monitor",
    "Evaluator": "Phase 1 — Monitor",
    "Alert Router": "Phase 1 — Monitor",
    "Incident Creator": "Phase 1 — Monitor",
    "Notifier": "Phase 1 — Monitor",
    "Ticket Writer": "Phase 1 — Monitor",
    "RCA Agent": "Phase 2 — Triage",
    "Recommender": "Phase 2 — Triage",
    "Enricher": "Phase 2 — Triage",
    "Solicitor": "Phase 3 — Approval",
    "Executor": "Phase 3 — Approval",
    "Ticket Updater": "Phase 3 — Approval",
    "Closer": "Phase 3 — Close",
    "Pipeline": "",
}
_B = {"success", "completed", "failed", "skipped", "suppressed"}


def _c(o: str) -> str:
    return o if o in _B else "default"


# ── Load & filter ─────────────────────────────────────────────────────
params = st.query_params
ticket_param = params.get("ticket", "")

df_all = _load()
if df_all.empty:
    st.info("No pipeline traces yet. Run a simulation to generate trace data.")
    st.stop()

if "ticket_number" not in df_all.columns:
    df_all["ticket_number"] = ""

ticket_list = sorted(df_all[df_all["ticket_number"] != ""]["ticket_number"].unique(), reverse=True)
incident_list = sorted(df_all[df_all["incident_id"] != ""]["incident_id"].unique(), reverse=True)

if ticket_param:
    st.title(f"Workflow — {ticket_param}")
    st.caption("Agent-by-agent pipeline trace. Click any node on the left to see its full detail on the right.")
    if ticket_param in df_all["ticket_number"].values:
        runs = df_all[df_all["ticket_number"] == ticket_param]["run_id"].unique()
    elif ticket_param in df_all["incident_id"].values:
        runs = df_all[df_all["incident_id"] == ticket_param]["run_id"].unique()
    else:
        st.warning(f"No trace for `{ticket_param}`.")
        st.stop()
    view = df_all[df_all["run_id"].isin(runs)]
else:
    st.title("Workflow Trace")
    st.caption("Select a ticket to view its pipeline, or browse all runs.")
    c1, c2 = st.columns(2)
    with c1:
        pick = st.selectbox("Ticket / Incident",
                            ["(select)"] + ticket_list + [f"inc: {i}" for i in incident_list], key="wf_pk")
    with c2:
        refresh_sec = st.selectbox("Auto-refresh", ["Off", "3 s", "5 s", "10 s"], key="wf_rf")

    if pick == "(select)":
        st.markdown("---")
        st.subheader("All pipeline runs")
        rs = (df_all.groupby("run_id").agg(
            timestamp=("timestamp", "min"), ticket=("ticket_number", "last"),
            incident_id=("incident_id", "last"), steps=("step_order", "count"),
            final_outcome=("outcome", "last")).reset_index().sort_values("timestamp", ascending=False))
        rs["display"] = rs.apply(lambda r: r["ticket"] if r["ticket"] else r["incident_id"], axis=1)
        st.dataframe(rs[["run_id", "display", "timestamp", "steps", "final_outcome"]].rename(
            columns={"display": "ticket / incident"}), use_container_width=True, hide_index=True)
        st.stop()

    if pick.startswith("inc: "):
        view = df_all[df_all["incident_id"] == pick[5:]]
    else:
        view = df_all[df_all["ticket_number"] == pick]
    if view.empty:
        st.warning("No trace data.")
        st.stop()

# ── Prepare rows ──────────────────────────────────────────────────────
view = view.copy()
view["step_order"] = pd.to_numeric(view["step_order"], errors="coerce")
view = view.sort_values(["run_id", "step_order"])
steps = [r for _, r in view.iterrows() if r["outcome"] != "started"]

t_nums = view[view["ticket_number"] != ""]["ticket_number"].unique()
inc_ids = view[view["incident_id"] != ""]["incident_id"].unique()
disp_t = ", ".join(t_nums) if len(t_nums) else "—"
disp_i = ", ".join(inc_ids) if len(inc_ids) else "—"

st.markdown(
    f'<div class="wf-bar">'
    f'<span><b>Ticket:</b> <code>{disp_t}</code></span>'
    f'<span><b>Incident:</b> <code>{disp_i}</code></span>'
    f'<span><b>Steps:</b> {len(steps)}</span>'
    f'</div>', unsafe_allow_html=True)

if ticket_param:
    if st.button("← Back to Tickets"):
        st.query_params.clear()
        st.switch_page("pages/4_Tickets.py")

st.markdown("---")

# ── Session state for selected step ──────────────────────────────────
if "wf_sel" not in st.session_state:
    st.session_state["wf_sel"] = 0

# ── Two-column layout ────────────────────────────────────────────────
col_flow, col_detail = st.columns([2, 3], gap="large")

with col_flow:
    st.markdown("##### Pipeline Flow")
    prev_phase = ""
    for i, row in enumerate(steps):
        agent = row["agent"]
        phase = PHASES.get(agent, "")

        if phase and phase != prev_phase:
            st.markdown(f'<div class="phase-sep">{phase}</div>', unsafe_allow_html=True)
            prev_phase = phase
        elif i > 0 and steps[i - 1]["agent"] != agent:
            st.markdown('<div class="fn-arrow">↓</div>', unsafe_allow_html=True)

        icon = ICONS.get(agent, "🔹")
        outcome = row["outcome"]
        c = _c(outcome)
        sn = int(row["step_order"]) if pd.notna(row["step_order"]) else "?"
        sel_class = " fn-selected" if i == st.session_state["wf_sel"] else ""

        st.markdown(
            f'<div class="fn fn-{c}{sel_class}">'
            f'<div class="fn-head">'
            f'<span class="fn-agent">{icon} {agent}</span>'
            f'<span class="fn-badge fn-badge-{c}">{outcome}</span>'
            f'</div>'
            f'<div class="fn-decision">{row["decision"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(f"Step {sn}", key=f"sel_{i}", use_container_width=True,
                      type="tertiary" if i != st.session_state["wf_sel"] else "primary"):
            st.session_state["wf_sel"] = i
            st.rerun()

# ── Detail panel ─────────────────────────────────────────────────────
with col_detail:
    st.markdown("##### Step Detail")
    sel_idx = st.session_state.get("wf_sel", 0)
    if sel_idx < len(steps):
        s = steps[sel_idx]
        agent = s["agent"]
        icon = ICONS.get(agent, "🔹")
        outcome = s["outcome"]
        c = _c(outcome)
        sn = int(s["step_order"]) if pd.notna(s["step_order"]) else "?"

        st.markdown(
            f'<div class="dp">'
            f'<div class="dp-title">{icon} {agent} <span class="fn-badge fn-badge-{c}">{outcome}</span></div>'

            f'<div class="dp-field"><div class="dp-label">Step</div><div class="dp-val">{sn}</div></div>'
            f'<div class="dp-field"><div class="dp-label">Action</div><div class="dp-val">{s["action"]}</div></div>'
            f'<div class="dp-field"><div class="dp-label">Decision</div><div class="dp-val">{s["decision"]}</div></div>'
            f'<div class="dp-field"><div class="dp-label">Timestamp</div><div class="dp-val">{s["timestamp"]}</div></div>'

            f'<div class="dp-field">'
            f'<div class="dp-label">Rationale</div>'
            f'<div class="dp-rationale">💬 {s["rationale"]}</div>'
            f'</div>'

            + (f'<div class="dp-field"><div class="dp-label">Detail</div>'
               f'<div class="dp-val">📎 {s["detail"]}</div></div>' if s["detail"] else "")

            + (f'<div class="dp-field"><div class="dp-label">Ticket</div>'
               f'<div class="dp-val">{s["ticket_number"]}</div></div>' if s.get("ticket_number") else "")

            + (f'<div class="dp-field"><div class="dp-label">Incident</div>'
               f'<div class="dp-val">{s["incident_id"]}</div></div>' if s.get("incident_id") else "")

            + f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("Select a step on the left to view details.")

# ── Raw table ─────────────────────────────────────────────────────────
with st.expander("Raw trace table"):
    st.dataframe(view, use_container_width=True, hide_index=True)

# ── Auto-refresh ──────────────────────────────────────────────────────
if not ticket_param:
    _RM = {"Off": 0, "3 s": 3, "5 s": 5, "10 s": 10}
    iv = _RM.get(refresh_sec, 0)
    if iv > 0:
        time.sleep(iv)
        st.rerun()
