"""
Simulate issues: trigger simulator scenarios; events create incidents (and optionally tickets).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import asyncio
import httpx
from simulator.scenarios import list_scenarios, emit_event

st.title("Simulate issues")
st.caption("Emit events that flow through Collector → Evaluator → Alert Router → Incident Creator.")

scenarios = list_scenarios()
scenario = st.selectbox("Scenario", scenarios)
count = st.number_input("Count", min_value=1, max_value=10, value=1)
use_api = st.checkbox("POST to orchestrator (requires API running)", value=False)
if use_api:
    base_url = st.text_input("Orchestrator URL", value="http://127.0.0.1:8000", key="orch_url")
else:
    base_url = "http://127.0.0.1:8000"

if st.button("Emit"):
    if use_api:
        async def run():
            async with httpx.AsyncClient() as client:
                for _ in range(count):
                    ev = emit_event(scenario)
                    r = await client.post(f"{base_url}/events", json={"event_id": ev["event_id"], "type": "simulated", "payload": ev})
                    r.raise_for_status()
        try:
            asyncio.run(run())
            st.success(f"Emitted {count} event(s) to orchestrator.")
        except Exception as e:
            st.error(str(e))
    else:
        # Run monitor pipeline in-process so incidents are created without API
        from orchestrator.router import handle_event
        for _ in range(count):
            ev = emit_event(scenario)
            asyncio.run(handle_event({"event_id": ev["event_id"], "type": "simulated", "payload": ev}))
        st.success(f"Emitted {count} event(s) and ran monitor pipeline locally. Check Overview or Tickets.")
