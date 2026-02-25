"""
Overview dashboard: recent incidents, agent actions, audit log tail.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import DATA_DIR

st.title("Overview")
st.caption("Recent incidents and audit log tail.")

incidents_path = DATA_DIR / "incidents" / "incidents.csv"
audit_path = DATA_DIR / "audit" / "simple.csv"

col1, col2 = st.columns(2)
with col1:
    st.subheader("Recent incidents")
    if incidents_path.exists():
        df = pd.read_csv(incidents_path)
        st.dataframe(df.tail(20), use_container_width=True, hide_index=True)
    else:
        st.info("No incidents yet. Use **Simulate issues** to create some.")

with col2:
    st.subheader("Audit log (simple) tail")
    if audit_path.exists():
        df = pd.read_csv(audit_path)
        st.dataframe(df.tail(30), use_container_width=True, hide_index=True)
    else:
        st.info("No audit entries yet.")
