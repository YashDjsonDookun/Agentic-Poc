"""
Tickets hub: list incidents (from local CSV); when Jira/ServiceNow configured, show ticket links.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import DATA_DIR

st.title("Tickets")
st.caption("Incidents (local CSV). Ticket links when Jira/ServiceNow configured.")

incidents_path = DATA_DIR / "incidents" / "incidents.csv"
if not incidents_path.exists():
    st.info("No incidents yet. Use **Simulate issues** to create some.")
    st.stop()

df = pd.read_csv(incidents_path)
status_filter = st.selectbox("Filter by severity", [""] + sorted(df["severity"].unique().tolist()))
if status_filter:
    df = df[df["severity"] == status_filter]
st.dataframe(df, use_container_width=True, hide_index=True)
st.markdown("When Jira/ServiceNow is configured, ticket IDs will appear; open in browser from there.")
