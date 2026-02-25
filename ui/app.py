"""
SENTRY/ARGUS — Central hub & control panel (Streamlit).
Run from project root: streamlit run ui/app.py
"""
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="SENTRY/ARGUS", page_icon="🛡️", layout="wide")
st.title("🛡️ SENTRY / ARGUS")
st.caption("Central hub & control panel — configure agents, view tickets, simulate issues, view logs.")

# Multi-page: Streamlit auto-adds pages from ui/pages/ to the sidebar.
st.sidebar.markdown("### Pages")
st.sidebar.markdown("Use the sidebar: **Overview** → **Configuration** → **Tables** → **Tickets** → **Simulate** → **Logs**.")

st.markdown("---")
st.markdown("""
- **Overview** — Dashboard: recent incidents, agent actions, audit tail.
- **Configuration** — View and edit config (agents, services, integrations). No secrets in UI.
- **Tables** — Edit tabular CSV config (alert rules, severity mapping, etc.); save locally.
- **Tickets** — List tickets (Jira/ServiceNow when configured); open in browser.
- **Simulate issues** — Trigger simulator scenarios; see incidents/tickets created.
- **Logs** — Toggle simple/comprehensive audit logs; filter by agent, action, date, outcome.
""")
