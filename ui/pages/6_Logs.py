"""
Dedicated Logs page: toggle simple vs comprehensive; filter by agent, action type, date range, outcome.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from shared.config_loader import DATA_DIR

st.title("Logs")
st.caption("Toggle simple vs comprehensive; filter audit log.")

AUDIT_DIR = DATA_DIR / "audit"
SIMPLE_PATH = AUDIT_DIR / "simple.csv"
COMPREHENSIVE_PATH = AUDIT_DIR / "comprehensive.csv"

log_type = st.radio("Log type", ["Simple", "Comprehensive"], horizontal=True)
path = COMPREHENSIVE_PATH if log_type == "Comprehensive" else SIMPLE_PATH

if not path.exists():
    st.info("No log file yet.")
    st.stop()

df = pd.read_csv(path)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    agents = [""] + sorted(df["agent_id"].dropna().unique().tolist()) if "agent_id" in df.columns else [""]
    agent = st.selectbox("Agent", agents)
with col2:
    actions = [""] + sorted(df["action_type"].dropna().unique().tolist()) if "action_type" in df.columns else [""]
    action = st.selectbox("Action type", actions)
with col3:
    outcomes = [""] + sorted(df["outcome"].dropna().unique().tolist()) if "outcome" in df.columns else [""]
    outcome = st.selectbox("Outcome", outcomes)

filtered = df
if agent:
    filtered = filtered[filtered["agent_id"] == agent]
if action:
    filtered = filtered[filtered["action_type"] == action]
if outcome:
    filtered = filtered[filtered["outcome"] == outcome]

st.dataframe(filtered, use_container_width=True, hide_index=True)
