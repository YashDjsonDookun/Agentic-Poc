"""
Edit tabular config (CSV): alert rules, severity_priority, maintenance_windows, services. Save locally.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import CONFIG_TABLES_DIR

st.title("Tables (CSV config)")
st.caption("Edit tabular data; save writes back to CSV locally.")

TABLES = {
    "alert_rules": "alert_rules.csv",
    "severity_priority": "severity_priority.csv",
    "maintenance_windows": "maintenance_windows.csv",
    "services": "services.csv",
}

choice = st.selectbox("Select table", list(TABLES.keys()))
path = CONFIG_TABLES_DIR / TABLES[choice]

if not path.exists():
    st.warning(f"File not found: {path}")
    st.stop()

df = pd.read_csv(path)
edited = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")

if st.button("Save to CSV"):
    edited.to_csv(path, index=False)
    st.success(f"Saved to {path}")
