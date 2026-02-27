"""
Live Pipeline — real-time view of the orchestrator processing events.
Always-on polling: detects new pipeline runs as soon as they appear.
Nodes materialise progressively as each agent makes decisions; the active step pulses.
"""
import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.trace import TRACE_PATH

# ═══════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""<style>
@keyframes pulse-border {
  0%   { box-shadow: 0 0 0 0 rgba(52,152,219,0.55); }
  70%  { box-shadow: 0 0 0 10px rgba(52,152,219,0); }
  100% { box-shadow: 0 0 0 0 rgba(52,152,219,0); }
}
@keyframes slide-in {
  from { opacity:0; transform: translateY(12px); }
  to   { opacity:1; transform: translateY(0); }
}
@keyframes dot-blink {
  0%, 80%, 100% { opacity: 0.15; }
  40% { opacity: 1; }
}
@keyframes waiting-pulse {
  0%, 100% { opacity: 0.4; }
  50%      { opacity: 1; }
}

.live-dot { display:inline-block;width:9px;height:9px;border-radius:50%;
            background:#2ecc71;margin-right:6px;animation:pulse-border 1.5s infinite; }
.done-dot { display:inline-block;width:9px;height:9px;border-radius:50%;
            background:#95a5a6;margin-right:6px; }
.pin-dot  { display:inline-block;width:9px;height:9px;border-radius:50%;
            background:#f39c12;margin-right:6px; }

/* waiting state */
.waiting-box { text-align:center; padding:60px 20px; border-radius:14px;
               background:rgba(52,152,219,0.06); border:2px dashed rgba(52,152,219,0.25);
               margin:30px auto; max-width:500px; }
.waiting-box h3 { margin:0 0 8px 0; animation: waiting-pulse 2s ease-in-out infinite; }
.waiting-box p { opacity:0.5; margin:0; font-size:0.92em; }

/* timeline */
.tl { position:relative; padding-left:36px; }
.tl::before { content:''; position:absolute; left:16px; top:0; bottom:0;
              width:2px; background:rgba(128,128,128,0.18); }

/* node dot */
.nd { position:relative; margin-bottom:18px; animation: slide-in 0.35s ease-out both; }
.nd::before { content:''; position:absolute; left:-26px; top:14px;
              width:14px; height:14px; border-radius:50%; border:2px solid #555;
              background:var(--bg, #222); z-index:1; }
.nd-done::before   { background:#2ecc71; border-color:#2ecc71; }
.nd-fail::before   { background:#e74c3c; border-color:#e74c3c; }
.nd-skip::before   { background:#95a5a6; border-color:#95a5a6; }
.nd-warn::before   { background:#f39c12; border-color:#f39c12; }
.nd-active::before { background:#3498db; border-color:#3498db;
                     animation: pulse-border 1.4s infinite; }
.nd-future::before { background:transparent; border-color:rgba(128,128,128,0.3); }

/* node card */
.nc { border-radius:10px; padding:14px 18px; }
.nc-done   { background:rgba(46,204,113,0.07);  border-left:4px solid #2ecc71; }
.nc-fail   { background:rgba(231,76,60,0.07);   border-left:4px solid #e74c3c; }
.nc-skip   { background:rgba(149,165,166,0.07); border-left:4px solid #95a5a6; }
.nc-warn   { background:rgba(243,156,18,0.07);  border-left:4px solid #f39c12; }
.nc-active { background:rgba(52,152,219,0.10);  border:2px solid rgba(52,152,219,0.6);
             animation: pulse-border 1.4s infinite; }
.nc-future { background:rgba(128,128,128,0.04); border-left:4px solid rgba(128,128,128,0.2);
             opacity:0.35; }

.nc-head { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; }
.nc-agent { font-weight:800; font-size:1.08em; }
.nc-badge { display:inline-block; padding:2px 10px; border-radius:12px;
            font-size:0.72em; font-weight:700; color:#fff; }
.bg-success,.bg-completed { background:#2ecc71; }
.bg-failed  { background:#e74c3c; }
.bg-skipped,.bg-suppressed { background:#95a5a6; }
.bg-warning { background:#f39c12; }
.bg-started { background:#3498db; }
.bg-default { background:#3498db; }
.nc-decision { font-size:0.92em; margin-top:6px; font-weight:600; }
.nc-rationale { font-size:0.88em; opacity:0.75; margin-top:4px; line-height:1.55;
                padding:8px 12px; border-radius:6px; background:rgba(128,128,128,0.06); }
.nc-detail { font-size:0.82em; opacity:0.5; margin-top:4px; }
.nc-ts { font-size:0.72em; opacity:0.35; margin-top:4px; }

.thinking { display:inline-flex; gap:4px; margin-left:8px; }
.thinking span { width:6px; height:6px; border-radius:50%; background:#3498db; display:inline-block; }
.thinking span:nth-child(1) { animation: dot-blink 1.4s infinite 0s; }
.thinking span:nth-child(2) { animation: dot-blink 1.4s infinite 0.2s; }
.thinking span:nth-child(3) { animation: dot-blink 1.4s infinite 0.4s; }

.pbar-wrap { background:rgba(128,128,128,0.12); border-radius:8px; height:10px;
             margin:8px 0 14px 0; overflow:hidden; }
.pbar-fill { height:100%; border-radius:8px; transition:width 0.5s ease;
             background:linear-gradient(90deg,#3498db,#2ecc71); }

.itile { text-align:center; padding:12px 8px; border-radius:10px;
         background:rgba(128,128,128,0.05); }
.itile-n { font-size:1.6em; font-weight:800; }
.itile-l { font-size:0.78em; opacity:0.5; text-transform:uppercase; letter-spacing:0.5px; }

.phase-hdr { font-size:0.75em; font-weight:700; opacity:0.4; text-transform:uppercase;
             letter-spacing:1.2px; padding:6px 0 2px 0; margin-top:4px;
             border-top:1px dashed rgba(128,128,128,0.15); }
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════
ICONS = {
    "Collector": "📥", "Evaluator": "📊", "Alert Router": "🚦",
    "Incident Creator": "🆕", "Correlator": "🔗", "Notifier": "📢",
    "Ticket Writer": "🎫", "RCA Agent": "🔍", "Recommender": "📚",
    "Enricher": "✏️", "Solicitor": "🤝", "Executor": "⚙️",
    "Ticket Updater": "🔄", "Closer": "🔒", "CascadeCloser": "🔒",
    "Pipeline": "🏁", "Aggregator": "📦", "Doc Writer": "📝",
    "Publisher": "📤", "Chronicler": "📖",
}
PHASES = {
    "Collector": "Phase 1 — Monitoring",
    "Evaluator": "Phase 1 — Monitoring",
    "Alert Router": "Phase 1 — Monitoring",
    "Incident Creator": "Phase 1 — Monitoring",
    "Correlator": "Phase 1 — Correlation",
    "Notifier": "Phase 1 — Notification",
    "Ticket Writer": "Phase 1 — Ticketing",
    "RCA Agent": "Phase 2 — Root Cause Analysis",
    "Recommender": "Phase 2 — Recommendation",
    "Enricher": "Phase 2 — Enrichment",
    "Solicitor": "Phase 3 — Human Approval",
    "Executor": "Phase 3 — Execution",
    "Ticket Updater": "Phase 3 — Ticket Update",
    "Closer": "Phase 3 — Closure",
    "CascadeCloser": "Phase 3 — Cascade Closure",
    "Aggregator": "Phase 4 — Documentation",
    "Doc Writer": "Phase 4 — Documentation",
    "Publisher": "Phase 4 — Documentation",
    "Chronicler": "Phase 4 — Documentation",
    "Pipeline": "",
}
EXPECTED_AGENTS = [
    "Collector", "Evaluator", "Alert Router", "Incident Creator",
    "Correlator", "Notifier", "Ticket Writer",
    "RCA Agent", "Recommender", "Enricher",
    "Solicitor", "Pipeline",
]

_RATES = {"1s": 1, "2s": 2, "3s": 3, "5s": 5}
REFRESH_DEFAULT = "2s"


def _outcome_class(outcome: str) -> str:
    o = outcome.lower()
    if o in ("success", "completed"):
        return "done"
    if o == "failed":
        return "fail"
    if o in ("skipped", "suppressed"):
        return "skip"
    if o in ("warning", "reopen_alert"):
        return "warn"
    if o == "started":
        return "active"
    return "done"


def _badge_class(outcome: str) -> str:
    o = outcome.lower()
    if o in ("success", "completed"):
        return "bg-success"
    if o == "failed":
        return "bg-failed"
    if o in ("skipped", "suppressed"):
        return "bg-skipped"
    if o in ("warning", "reopen_alert"):
        return "bg-warning"
    if o == "started":
        return "bg-started"
    return "bg-default"


def _load() -> pd.DataFrame:
    if not TRACE_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(TRACE_PATH, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def _file_mtime() -> float:
    """Return trace file mtime for change detection."""
    try:
        return TRACE_PATH.stat().st_mtime if TRACE_PATH.exists() else 0
    except OSError:
        return 0


def _get_latest_run_id(df: pd.DataFrame) -> str:
    """Return the run_id with the most recent timestamp."""
    if df.empty or "timestamp" not in df.columns:
        return ""
    df2 = df.copy()
    df2["_ts"] = pd.to_datetime(df2["timestamp"], errors="coerce")
    latest = df2.groupby("run_id")["_ts"].max().sort_values(ascending=False)
    return latest.index[0] if len(latest) > 0 else ""


# ═══════════════════════════════════════════════════════════════════════
# Session state — track file changes and auto-follow latest run
# ═══════════════════════════════════════════════════════════════════════
if "lp_pinned_run" not in st.session_state:
    st.session_state["lp_pinned_run"] = None  # None = follow latest automatically
if "lp_last_mtime" not in st.session_state:
    st.session_state["lp_last_mtime"] = 0

# ═══════════════════════════════════════════════════════════════════════
# Page header & controls
# ═══════════════════════════════════════════════════════════════════════
st.title("Live Pipeline")
st.caption("Always-on monitoring. Automatically detects new events and shows agent decisions in real-time.")

ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 2])
with ctrl1:
    refresh_rate = st.selectbox("Polling interval", list(_RATES.keys()),
                                index=list(_RATES.keys()).index(REFRESH_DEFAULT), key="lp_rf")
with ctrl2:
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    following_latest = st.session_state["lp_pinned_run"] is None
    if following_latest:
        st.markdown('<span><span class="live-dot"></span> <b>LIVE</b> — auto-following latest</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            f'<span><span class="pin-dot"></span> <b>PINNED</b> — {st.session_state["lp_pinned_run"][:20]}</span>',
            unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────
df_all = _load()

# ── If no data at all, show waiting state and keep polling ────────────
if df_all.empty:
    st.markdown(
        '<div class="waiting-box">'
        '<h3>📡 Listening for events...</h3>'
        '<p>Trigger a simulation or send an event to the orchestrator.<br>'
        'This page will automatically show the pipeline when it starts.</p>'
        '</div>', unsafe_allow_html=True)
    time.sleep(_RATES.get(refresh_rate, 2))
    st.rerun()

# ── Build recent runs list ────────────────────────────────────────────
df_all["_ts"] = pd.to_datetime(df_all["timestamp"], errors="coerce") if "timestamp" in df_all.columns else pd.NaT
run_latest = df_all.groupby("run_id")["_ts"].max().sort_values(ascending=False).head(20)

latest_run_id = run_latest.index[0] if len(run_latest) > 0 else ""

# Auto-follow: if not pinned, always use the latest run
if st.session_state["lp_pinned_run"] is None:
    selected_run = latest_run_id
else:
    selected_run = st.session_state["lp_pinned_run"]
    if selected_run not in run_latest.index:
        st.session_state["lp_pinned_run"] = None
        selected_run = latest_run_id

# ── Run selector (for pinning to a specific historical run) ───────────
with ctrl3:
    run_choices = list(run_latest.index)
    run_display = {}
    for rid in run_choices:
        subset = df_all[df_all["run_id"] == rid]
        ticket = subset["ticket_number"].iloc[-1] if "ticket_number" in subset.columns else ""
        inc = subset["incident_id"].iloc[-1] if "incident_id" in subset.columns else ""
        ts = run_latest[rid]
        ts_str = ts.strftime("%H:%M:%S") if pd.notna(ts) else "?"
        label = ticket or inc or rid[:16]
        prefix = "🔴 " if rid == latest_run_id else ""
        run_display[rid] = f"{prefix}{label} ({ts_str})"

    auto_label = f"🔴 Auto (latest: {run_display.get(latest_run_id, '?')})"
    pick_options = ["__auto__"] + run_choices
    pick_labels = [auto_label] + [run_display[r] for r in run_choices]

    current_idx = 0
    if st.session_state["lp_pinned_run"] is not None and st.session_state["lp_pinned_run"] in run_choices:
        current_idx = run_choices.index(st.session_state["lp_pinned_run"]) + 1

    picked_idx = st.selectbox("Pipeline run", range(len(pick_options)),
                              index=current_idx,
                              format_func=lambda i: pick_labels[i], key="lp_pick")
    picked_val = pick_options[picked_idx]
    if picked_val == "__auto__":
        if st.session_state["lp_pinned_run"] is not None:
            st.session_state["lp_pinned_run"] = None
            st.rerun()
    else:
        if st.session_state["lp_pinned_run"] != picked_val:
            st.session_state["lp_pinned_run"] = picked_val
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# Filter data for the active run
# ═══════════════════════════════════════════════════════════════════════
run_df = df_all[df_all["run_id"] == selected_run].copy()
run_df["step_order"] = pd.to_numeric(run_df["step_order"], errors="coerce")
run_df = run_df.sort_values(["step_order", "_ts"])

if run_df.empty:
    st.markdown(
        '<div class="waiting-box">'
        '<h3>📡 Listening for events...</h3>'
        '<p>No active pipeline. Trigger a simulation — nodes will appear here automatically.</p>'
        '</div>', unsafe_allow_html=True)
    time.sleep(_RATES.get(refresh_rate, 2))
    st.rerun()

# Build step map
steps_map: dict[int, dict] = {}
for _, row in run_df.iterrows():
    sn = int(row["step_order"]) if pd.notna(row["step_order"]) else 0
    agent = row["agent"]
    outcome = row["outcome"]
    if sn not in steps_map:
        steps_map[sn] = {"started": None, "result": None, "agent": agent}
    if outcome == "started":
        steps_map[sn]["started"] = row
    else:
        steps_map[sn]["result"] = row
        steps_map[sn]["agent"] = agent

sorted_steps = sorted(steps_map.keys())

pipeline_done = any(
    steps_map[k]["result"] is not None
    and steps_map[k]["agent"] == "Pipeline"
    and steps_map[k]["result"]["outcome"] in ("completed",)
    for k in sorted_steps
)
completed_count = sum(1 for k in sorted_steps if steps_map[k]["result"] is not None)
total_visible = len(sorted_steps)

# ═══════════════════════════════════════════════════════════════════════
# Info tiles
# ═══════════════════════════════════════════════════════════════════════
t_nums = run_df[run_df["ticket_number"] != ""]["ticket_number"].unique()
inc_ids = run_df[run_df["incident_id"] != ""]["incident_id"].unique()

i1, i2, i3, i4 = st.columns(4)
with i1:
    disp = ", ".join(t_nums) if len(t_nums) else "Pending..."
    st.markdown(f'<div class="itile"><div class="itile-n">{disp}</div>'
                f'<div class="itile-l">Ticket</div></div>', unsafe_allow_html=True)
with i2:
    disp = ", ".join(inc_ids[:2]) if len(inc_ids) else "—"
    st.markdown(f'<div class="itile"><div class="itile-n">{disp}</div>'
                f'<div class="itile-l">Incident</div></div>', unsafe_allow_html=True)
with i3:
    st.markdown(f'<div class="itile"><div class="itile-n">{completed_count}/{total_visible}</div>'
                f'<div class="itile-l">Steps</div></div>', unsafe_allow_html=True)
with i4:
    if pipeline_done:
        status_label, status_color = "Complete", "#2ecc71"
    else:
        status_label, status_color = "In Progress", "#3498db"
    st.markdown(f'<div class="itile"><div class="itile-n" style="color:{status_color};">{status_label}</div>'
                f'<div class="itile-l">Status</div></div>', unsafe_allow_html=True)

pct = int(completed_count / max(total_visible, 1) * 100) if total_visible else 0
bar_color = "background:linear-gradient(90deg,#2ecc71,#27ae60);" if pipeline_done else ""
st.markdown(f'<div class="pbar-wrap"><div class="pbar-fill" style="width:{pct}%;{bar_color}"></div></div>',
            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# Timeline
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")

html_parts = ['<div class="tl">']
prev_phase = ""

for k in sorted_steps:
    info = steps_map[k]
    agent = info["agent"]
    started = info["started"]
    result = info["result"]

    phase = PHASES.get(agent, "")
    if phase and phase != prev_phase:
        html_parts.append(f'<div class="phase-hdr">{phase}</div>')
        prev_phase = phase

    if result is not None:
        row = result
        outcome = row["outcome"]
        nc = _outcome_class(outcome)
        is_active = False
    elif started is not None:
        row = started
        outcome = "started"
        nc = "active"
        is_active = True
    else:
        continue

    icon = ICONS.get(agent, "🔹")
    decision = row["decision"] if row["decision"] else ""
    rationale = row["rationale"] if row["rationale"] else ""
    detail = row.get("detail", "")
    ts = row["timestamp"] if row["timestamp"] else ""
    badge = _badge_class(outcome)

    if is_active:
        thinking_html = '<div class="thinking"><span></span><span></span><span></span></div>'
        outcome_label = "Processing"
    else:
        thinking_html = ""
        outcome_label = outcome

    detail_html = ""
    if detail and not is_active:
        detail_html = f'<div class="nc-detail">📎 {detail}</div>'

    rationale_html = ""
    if rationale:
        emoji = "🧠" if is_active else "💬"
        rationale_html = f'<div class="nc-rationale">{emoji} {rationale}{thinking_html}</div>'

    html_parts.append(
        f'<div class="nd nd-{nc}">'
        f'<div class="nc nc-{nc}">'
        f'<div class="nc-head">'
        f'<span class="nc-agent">{icon} {agent}</span>'
        f'<span class="nc-badge {badge}">{outcome_label}</span>'
        f'</div>'
    )
    if decision:
        html_parts.append(f'<div class="nc-decision">{decision}</div>')
    if rationale_html:
        html_parts.append(rationale_html)
    if detail_html:
        html_parts.append(detail_html)
    if ts:
        html_parts.append(f'<div class="nc-ts">{ts}</div>')
    html_parts.append('</div></div>')

# Upcoming placeholders
if not pipeline_done and sorted_steps:
    seen_agents = {steps_map[k]["agent"] for k in sorted_steps}
    for ea in EXPECTED_AGENTS:
        if ea not in seen_agents:
            icon = ICONS.get(ea, "🔹")
            phase = PHASES.get(ea, "")
            if phase and phase != prev_phase:
                html_parts.append(f'<div class="phase-hdr">{phase}</div>')
                prev_phase = phase
            html_parts.append(
                f'<div class="nd nd-future"><div class="nc nc-future">'
                f'<div class="nc-head">'
                f'<span class="nc-agent">{icon} {ea}</span>'
                f'<span class="nc-badge bg-default" style="opacity:0.3;">pending</span>'
                f'</div></div></div>'
            )

html_parts.append('</div>')
st.markdown("".join(html_parts), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# Raw trace (collapsible)
# ═══════════════════════════════════════════════════════════════════════
with st.expander("Raw trace data"):
    show_cols = [c for c in run_df.columns if c != "_ts"]
    st.dataframe(run_df[show_cols], use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════
# ALWAYS poll — this is the key: never stop refreshing
# ═══════════════════════════════════════════════════════════════════════
iv = _RATES.get(refresh_rate, 2)
time.sleep(iv)
st.rerun()
