"""
Standalone simulator (1.6): CLI to emit one or more events. Can be run manually or from Streamlit.
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from simulator.scenarios import emit_event, list_scenarios

ORCHESTRATOR_URL = "http://127.0.0.1:8000"  # override with env if needed


def run_local(scenario_key: str, count: int = 1) -> list[dict]:
    """Emit events locally (returns list of event dicts). No HTTP."""
    events = []
    for _ in range(count):
        events.append(emit_event(scenario_key))
    return events


async def run_via_api(scenario_key: str, count: int = 1, base_url: str = ORCHESTRATOR_URL) -> list[dict]:
    """Emit events by POSTing to orchestrator /events."""
    events = []
    async with httpx.AsyncClient() as client:
        for _ in range(count):
            ev = emit_event(scenario_key)
            events.append(ev)
            r = await client.post(
                f"{base_url}/events",
                json={"event_id": ev["event_id"], "type": "simulated", "payload": ev},
            )
            r.raise_for_status()
    return events


def main():
    parser = argparse.ArgumentParser(description="Emit simulated issues (events) for SENTRY/ARGUS")
    parser.add_argument("scenario", nargs="?", choices=list_scenarios(), help="Scenario to run")
    parser.add_argument("-n", "--count", type=int, default=1, help="Number of events to emit")
    parser.add_argument("--api", action="store_true", help="POST to orchestrator (default: local only)")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--base-url", default=ORCHESTRATOR_URL, help="Orchestrator base URL when using --api")
    args = parser.parse_args()

    if args.list:
        print("Scenarios:", ", ".join(list_scenarios()))
        return

    if not args.scenario:
        parser.error("scenario required (or use --list)")
        return

    if args.api:
        events = asyncio.run(run_via_api(args.scenario, args.count, args.base_url))
    else:
        events = run_local(args.scenario, args.count)

    for e in events:
        print(e.get("event_id"), e.get("service"), e.get("metric"), e.get("value"))
    print(f"Emitted {len(events)} event(s).")


if __name__ == "__main__":
    main()
