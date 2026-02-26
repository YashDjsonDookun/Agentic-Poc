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
            async with httpx.AsyncClient(timeout=30.0) as client:
                last = None
                for i in range(count):
                    ev = emit_event(scenario)
                    r = await client.post(f"{base_url}/events", json={"event_id": ev["event_id"], "type": "simulated", "payload": ev})
                    last = r
                    if r.status_code >= 400:
                        err_body = r.text
                        try:
                            j = r.json()
                            err_body = j.get("detail", err_body) if isinstance(j.get("detail"), str) else (str(j) if j else err_body)
                        except Exception:
                            pass
                        raise httpx.HTTPStatusError(f"HTTP {r.status_code}: {err_body or r.reason_phrase}", request=r.request, response=r)
                return last
        try:
            r = asyncio.run(run())
            st.success(f"Emitted {count} event(s) to orchestrator.")
            if r and r.status_code == 200:
                try:
                    body = r.json()
                    ticket = body.get("ticket") or {}
                    if ticket.get("jira_error"):
                        st.warning(f"Ticket created in ServiceNow. Jira failed: {ticket['jira_error']}")
                except Exception:
                    pass
        except httpx.HTTPStatusError as e:
            msg = e.response.text if e.response else str(e)
            if not msg:
                msg = f"HTTP {e.response.status_code}" if e.response else str(e)
            st.error(f"Orchestrator error: {msg}")
        except httpx.RequestError as e:
            st.error(f"Connection error: {str(e) or 'Could not reach orchestrator. Is it running at ' + base_url + '?'}")
        except Exception as e:
            st.error(str(e) or repr(e))
    else:
        # Run monitor pipeline in-process so incidents are created without API
        from orchestrator.router import handle_event
        last_result = None
        for _ in range(count):
            ev = emit_event(scenario)
            last_result = asyncio.run(handle_event({"event_id": ev["event_id"], "type": "simulated", "payload": ev}))
        st.success(f"Emitted {count} event(s) and ran monitor pipeline locally. Check Overview or Tickets.")
        if last_result and (last_result.get("ticket") or {}).get("jira_error"):
            st.warning(f"Ticket created in ServiceNow. Jira failed: {last_result['ticket']['jira_error']}")
