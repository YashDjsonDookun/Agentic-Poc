"""
Logs page: Simple audit logs + Comprehensive pipeline trace with rich detail.
Simple = data/audit/simple.csv (lightweight action log).
Comprehensive = data/trace/trace.csv (full pipeline detail with decisions & rationale).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import DATA_DIR
from shared.trace import TRACE_PATH

st.title("Logs")
st.caption("Simple audit trail and comprehensive pipeline trace.")

SIMPLE_PATH = DATA_DIR / "audit" / "simple.csv"

# ── CSS ───────────────────────────────────────────────────────────────
st.markdown("""<style>
.log-card {border-radius:8px;padding:10px 14px;margin-bottom:6px;background:rgba(128,128,128,0.05);}
.log-card-success,.log-card-completed {border-left:4px solid #2ecc71;}
.log-card-failed {border-left:4px solid #e74c3c;}
.log-card-skipped {border-left:4px solid #95a5a6;}
.log-card-suppressed {border-left:4px solid #f39c12;}
.log-card-default {border-left:4px solid #3498db;}
.log-head {display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;}
.log-agent {font-weight:700;font-size:1em;}
.log-ts {font-size:0.74em;opacity:0.45;}
.log-body {font-size:0.9em;margin-top:4px;}
.log-field {display:inline-block;margin-right:14px;}
.log-lbl {font-size:0.78em;font-weight:600;opacity:0.55;text-transform:uppercase;}
.log-val {font-size:0.88em;}
.log-rationale {font-size:0.88em;padding:6px 10px;border-radius:6px;background:rgba(128,128,128,0.07);margin-top:4px;line-height:1.45;}
.log-badge {display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.72em;font-weight:600;color:#fff;}
.log-badge-success,.log-badge-completed {background:#2ecc71;}
.log-badge-failed {background:#e74c3c;}
.log-badge-skipped {background:#95a5a6;}
.log-badge-suppressed {background:#f39c12;}
.log-badge-default {background:#3498db;}
</style>""", unsafe_allow_html=True)

_B = {"success", "completed", "failed", "skipped", "suppressed"}


def _c(o: str) -> str:
    return o if o in _B else "default"


# ── Tab selector ──────────────────────────────────────────────────────
tab_simple, tab_comp = st.tabs(["Simple", "Comprehensive"])

# ══════════════════════════════════════════════════════════════════════
# SIMPLE TAB
# ══════════════════════════════════════════════════════════════════════
with tab_simple:
    st.markdown("##### Audit Trail")
    st.caption("Lightweight action log — agent, action, entity, outcome.")

    if not SIMPLE_PATH.exists():
        st.info("No simple audit log yet. Run a simulation first.")
    else:
        df_s = pd.read_csv(SIMPLE_PATH, dtype=str).fillna("")
        if df_s.empty:
            st.info("Audit log is empty.")
        else:
            if "timestamp" in df_s.columns:
                df_s["timestamp"] = pd.to_datetime(df_s["timestamp"], errors="coerce")
                df_s = df_s.sort_values("timestamp", ascending=False)

            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                s_sort = st.selectbox("Sort", [
                    "Newest first", "Oldest first", "agent_id", "action_type", "outcome"
                ], key="s_sort")
            with fc2:
                agents = ["All"] + sorted(df_s["agent_id"].dropna().unique().tolist()) if "agent_id" in df_s.columns else ["All"]
                s_agent = st.selectbox("Agent", agents, key="s_ag")
            with fc3:
                actions = ["All"] + sorted(df_s["action_type"].dropna().unique().tolist()) if "action_type" in df_s.columns else ["All"]
                s_action = st.selectbox("Action", actions, key="s_act")
            with fc4:
                outcomes = ["All"] + sorted(df_s["outcome"].dropna().unique().tolist()) if "outcome" in df_s.columns else ["All"]
                s_outcome = st.selectbox("Outcome", outcomes, key="s_out")

            if s_sort == "Oldest first" and "timestamp" in df_s.columns:
                df_s = df_s.sort_values("timestamp", ascending=True)
            elif s_sort == "agent_id" and "agent_id" in df_s.columns:
                df_s = df_s.sort_values("agent_id")
            elif s_sort == "action_type" and "action_type" in df_s.columns:
                df_s = df_s.sort_values("action_type")
            elif s_sort == "outcome" and "outcome" in df_s.columns:
                df_s = df_s.sort_values("outcome")

            if s_agent != "All":
                df_s = df_s[df_s["agent_id"] == s_agent]
            if s_action != "All":
                df_s = df_s[df_s["action_type"] == s_action]
            if s_outcome != "All":
                df_s = df_s[df_s["outcome"] == s_outcome]

            st.dataframe(df_s, use_container_width=True, hide_index=True)
            st.caption(f"{len(df_s)} entries")

# ══════════════════════════════════════════════════════════════════════
# COMPREHENSIVE TAB (pipeline trace)
# ══════════════════════════════════════════════════════════════════════
with tab_comp:
    st.markdown("##### Comprehensive Pipeline Trace")
    st.caption("Full detail for every agent step — decisions, rationale, and context.")

    if not TRACE_PATH.exists():
        st.info("No pipeline trace yet. Run a simulation first.")
    else:
        df_t = pd.read_csv(TRACE_PATH, dtype=str).fillna("")
        if df_t.empty:
            st.info("Trace is empty.")
        else:
            if "ticket_number" not in df_t.columns:
                df_t["ticket_number"] = ""
            if "timestamp" in df_t.columns:
                df_t["timestamp"] = pd.to_datetime(df_t["timestamp"], errors="coerce")
                df_t = df_t.sort_values("timestamp", ascending=False)

            # Skip "started" rows — they're just invoke markers
            df_t = df_t[df_t["outcome"] != "started"]

            # Filters
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                t_agents = ["All"] + sorted(df_t["agent"].dropna().unique().tolist())
                t_agent = st.selectbox("Agent", t_agents, key="t_ag")
            with fc2:
                t_outcomes = ["All"] + sorted(df_t["outcome"].dropna().unique().tolist())
                t_outcome = st.selectbox("Outcome", t_outcomes, key="t_out")
            with fc3:
                t_tickets = ["All"] + sorted(df_t[df_t["ticket_number"] != ""]["ticket_number"].unique().tolist(), reverse=True)
                t_ticket = st.selectbox("Ticket", t_tickets, key="t_tk")
            with fc4:
                t_sort = st.selectbox("Sort", ["Newest first", "Oldest first", "Agent", "Outcome"], key="t_sort")

            if t_agent != "All":
                df_t = df_t[df_t["agent"] == t_agent]
            if t_outcome != "All":
                df_t = df_t[df_t["outcome"] == t_outcome]
            if t_ticket != "All":
                df_t = df_t[df_t["ticket_number"] == t_ticket]

            if t_sort == "Oldest first" and "timestamp" in df_t.columns:
                df_t = df_t.sort_values("timestamp", ascending=True)
            elif t_sort == "Agent":
                df_t = df_t.sort_values("agent")
            elif t_sort == "Outcome":
                df_t = df_t.sort_values("outcome")

            st.caption(f"{len(df_t)} entries")

            ICONS = {
                "Collector": "📥", "Evaluator": "📊", "Alert Router": "🚦",
                "Incident Creator": "🆕", "Notifier": "📢", "Ticket Writer": "🎫",
                "RCA Agent": "🔍", "Recommender": "📚", "Enricher": "✏️",
                "Solicitor": "🤝", "Executor": "⚙️", "Ticket Updater": "🔄",
                "Closer": "🔒", "Pipeline": "🏁",
            }

            for i, (_, row) in enumerate(df_t.head(50).iterrows()):
                agent = row.get("agent", "")
                icon = ICONS.get(agent, "🔹")
                outcome = row.get("outcome", "")
                c = _c(outcome)
                ticket = row.get("ticket_number", "")
                inc_id = row.get("incident_id", "")
                display_id = ticket or inc_id or "—"

                st.markdown(
                    f'<div class="log-card log-card-{c}">'
                    f'<div class="log-head">'
                    f'<span class="log-agent">{icon} {agent}</span>'
                    f'<span>'
                    f'<span class="log-badge log-badge-{c}">{outcome}</span> '
                    f'<span class="log-ts">{row.get("timestamp", "")}</span>'
                    f'</span></div>'
                    f'<div class="log-body">'
                    f'<span class="log-field"><span class="log-lbl">Ticket</span> <span class="log-val">{display_id}</span></span>'
                    f'<span class="log-field"><span class="log-lbl">Action</span> <span class="log-val">{row.get("action", "")}</span></span>'
                    f'<span class="log-field"><span class="log-lbl">Decision</span> <span class="log-val">{row.get("decision", "")}</span></span>'
                    f'<span class="log-field"><span class="log-lbl">Step</span> <span class="log-val">{row.get("step_order", "")}</span></span>'
                    f'</div>'
                    f'<div class="log-rationale">💬 {row.get("rationale", "")}</div>'
                    + (f'<div style="font-size:0.8em;opacity:0.5;margin-top:3px;">📎 {row.get("detail", "")}</div>'
                       if row.get("detail", "") else "")
                    + f'</div>',
                    unsafe_allow_html=True,
                )

                # Workflow link
                if display_id != "—":
                    if st.button(f"View Workflow → {display_id}", key=f"lg_wf_{i}"):
                        st.query_params["ticket"] = display_id
                        st.switch_page("pages/7_Workflow.py")

            # Raw table
            with st.expander("Full trace table"):
                st.dataframe(df_t, use_container_width=True, hide_index=True)
