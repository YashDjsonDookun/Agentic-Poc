"""
Configuration: view and edit YAML config from the UI.
Read-only by default; toggle edit mode to change values and save back to config files.
Integrations: configure URLs and credentials in the UI (stored in local file, not .env).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import asyncio
import streamlit as st
import yaml
from shared.config_loader import CONFIG_DIR, get_env, get_services_config, get_integrations_config

# Local integration credentials (UI-configured); fallback if loader was cached before these existed
try:
    from shared.config_loader import get_local_integrations, save_local_integrations
except ImportError:
    _local_integrations_path = CONFIG_DIR / "local.integrations.yaml"
    def get_local_integrations():
        if not _local_integrations_path.exists():
            return {}
        with open(_local_integrations_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    def save_local_integrations(data):
        _local_integrations_path.parent.mkdir(parents=True, exist_ok=True)
        with open(_local_integrations_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

st.title("Configuration")
st.caption("View and edit config. Integrations: set URLs and credentials in the UI and save.")

agents_path = CONFIG_DIR / "agents.yaml"
services_path = CONFIG_DIR / "services.yaml"
integrations_path = CONFIG_DIR / "integrations.yaml"
rag_path = CONFIG_DIR / "rag.yaml"


def load_yaml(p: Path) -> dict:
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# Edit mode toggle
if "config_edit_mode" not in st.session_state:
    st.session_state.config_edit_mode = False
edit_mode = st.session_state.config_edit_mode
if st.button("Toggle edit mode", type="primary"):
    st.session_state.config_edit_mode = not st.session_state.config_edit_mode
    st.rerun()
st.markdown(f"**Mode:** {'✏️ Edit (changes can be saved)' if st.session_state.config_edit_mode else '👁️ Read-only'}")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Agents", "Services", "Integrations", "RAG"])

# ---- Agents ----
with tab1:
    st.subheader("Agents (identities, enabled, timeouts)")
    data = load_yaml(agents_path)
    agents_data = data.get("agents") or {}

    if not st.session_state.config_edit_mode:
        for name, cfg in agents_data.items():
            with st.expander(name, expanded=True):
                if isinstance(cfg, dict):
                    st.text(f"Identity: {cfg.get('identity', '')}")
                    st.text(f"Enabled: {cfg.get('enabled', False)}")
                    st.text(f"Timeout (seconds): {cfg.get('timeout_seconds', '')}")
                    st.text(f"Description: {cfg.get('description', '')}")
        if not agents_data:
            st.info("No agents in config.")
    else:
        with st.form("agents_form"):
            new_agents = {}
            for agent_name, agent_cfg in agents_data.items():
                if not isinstance(agent_cfg, dict):
                    continue
                with st.expander(agent_name, expanded=True):
                    identity = st.text_input("Identity", value=str(agent_cfg.get("identity", "")), key=f"agents_{agent_name}_identity")
                    enabled = st.checkbox("Enabled", value=bool(agent_cfg.get("enabled", True)), key=f"agents_{agent_name}_enabled")
                    timeout_seconds = st.number_input("Timeout (seconds)", min_value=1, value=int(agent_cfg.get("timeout_seconds", 30)), key=f"agents_{agent_name}_timeout")
                    description = st.text_input("Description", value=str(agent_cfg.get("description", "")), key=f"agents_{agent_name}_description")
                new_agents[agent_name] = {"identity": identity, "enabled": enabled, "timeout_seconds": timeout_seconds, "description": description}

            if st.form_submit_button("Save to agents.yaml"):
                save_yaml(agents_path, {"agents": new_agents})
                st.success("Saved agents.yaml")
                st.rerun()

# ---- Services ----
with tab2:
    st.subheader("Services (LLM, Teams, Twilio, SMTP, RAG)")
    data = load_yaml(services_path)

    if not st.session_state.config_edit_mode:
        for name, cfg in (data or {}).items():
            if isinstance(cfg, dict):
                env_var_names = [v for k, v in cfg.items() if isinstance(v, str) and str(k).endswith("_env")]
                has_secret = any(get_env(n) for n in env_var_names) if env_var_names else False
                status = "✅ configured" if (cfg.get("enabled") and has_secret) else ("⚠️ disabled" if not cfg.get("enabled") else "❌ not configured")
                with st.expander(f"{name} — {status}", expanded=False):
                    st.text(f"Enabled: {cfg.get('enabled', False)}")
                    for k, v in cfg.items():
                        if k != "enabled" and isinstance(v, str):
                            st.text(f"{k}: {v}")
        if not data:
            st.info("No services in config.")
    else:
        with st.form("services_form"):
            new_services = {}
            for svc_name, svc_cfg in (data or {}).items():
                if not isinstance(svc_cfg, dict):
                    continue
                with st.expander(svc_name, expanded=False):
                    enabled = st.checkbox("Enabled", value=bool(svc_cfg.get("enabled", False)), key=f"svc_{svc_name}_enabled")
                    new_services[svc_name] = {"enabled": enabled}
                    for k, v in svc_cfg.items():
                        if k == "enabled":
                            continue
                        if isinstance(v, str):
                            val = st.text_input(k, value=v, key=f"svc_{svc_name}_{k}")
                            new_services[svc_name][k] = val
                        else:
                            new_services[svc_name][k] = v

            if st.form_submit_button("Save to services.yaml"):
                save_yaml(services_path, new_services)
                st.success("Saved services.yaml")
                st.rerun()

# ---- Integrations ----
with tab3:
    st.subheader("Integrations (ServiceNow, Jira)")
    data = load_yaml(integrations_path)
    from integrations import jira, servicenow
    from integrations.servicenow import test_connection as servicenow_test_connection
    from integrations.jira import test_connection as jira_test_connection

    # Test connection buttons (use saved config and UI-configured credentials)
    st.markdown("**Test connection** (uses saved Integration values below; success = 2xx response):")
    col_sn, col_jira, _ = st.columns([1, 1, 2])
    with col_sn:
        if st.button("Test ServiceNow connection", key="btn_test_servicenow"):
            with st.spinner("Testing ServiceNow…"):
                try:
                    ok, msg = asyncio.run(servicenow_test_connection())
                    st.session_state["test_servicenow_result"] = (ok, msg)
                except Exception as e:
                    st.session_state["test_servicenow_result"] = (False, str(e))
    with col_jira:
        if st.button("Test Jira connection", key="btn_test_jira"):
            with st.spinner("Testing Jira…"):
                try:
                    ok, msg = asyncio.run(jira_test_connection())
                    st.session_state["test_jira_result"] = (ok, msg)
                except Exception as e:
                    st.session_state["test_jira_result"] = (False, str(e))
    if "test_servicenow_result" in st.session_state:
        val = st.session_state["test_servicenow_result"]
        ok = val[0] if isinstance(val, (list, tuple)) else bool(val)
        msg = val[1] if isinstance(val, (list, tuple)) and len(val) > 1 else ("OK" if ok else "Failed")
        if ok:
            st.success(f"**ServiceNow**: OK ({msg})")
        else:
            st.error(f"**ServiceNow**: {msg}")
    if "test_jira_result" in st.session_state:
        val = st.session_state["test_jira_result"]
        ok = val[0] if isinstance(val, (list, tuple)) else bool(val)
        msg = val[1] if isinstance(val, (list, tuple)) and len(val) > 1 else ("OK" if ok else "Failed")
        if ok:
            st.success(f"**Jira**: OK ({msg})")
        else:
            st.error(f"**Jira**: {msg}")
    st.divider()

    local_creds = get_local_integrations()

    if not st.session_state.config_edit_mode:
        st.markdown(f"- **ServiceNow**: {'✅ configured' if servicenow.is_configured() else '❌ not configured'}")
        st.markdown(f"- **Jira**: {'✅ configured' if jira.is_configured() else '❌ not configured'}")
        for name, cfg in (data or {}).items():
            if isinstance(cfg, dict):
                creds = local_creds.get(name) or {}
                with st.expander(name, expanded=False):
                    st.text(f"Enabled: {cfg.get('enabled', False)}")
                    if name == "servicenow":
                        st.text(f"Instance URL: {'(set)' if creds.get('instance_url') else '(not set)'}")
                        st.text(f"Username: {'(set)' if creds.get('username') else '(not set)'}")
                        st.text(f"Password: {'(set)' if creds.get('password') else '(not set)'}")
                    elif name == "jira":
                        st.text(f"Base URL: {'(set)' if creds.get('base_url') else '(not set)'}")
                        st.text(f"Username: {'(set)' if creds.get('username') else '(not set)'}")
                        st.text(f"API token: {'(set)' if creds.get('api_token') else '(not set)'}")
                        st.text(f"Project key: {creds.get('project_key') or '(not set)'}")
        if not data:
            st.info("No integrations in config.")
    else:
        with st.form("integrations_form"):
            new_int = {}
            new_local = dict(local_creds)
            for name, cfg in (data or {}).items():
                if not isinstance(cfg, dict):
                    continue
                creds = new_local.get(name) or {}
                with st.expander(name, expanded=True):
                    enabled = st.checkbox("Enabled", value=bool(cfg.get("enabled", False)), key=f"int_{name}_enabled")
                    new_int[name] = {"enabled": enabled}
                    if name == "servicenow":
                        new_local.setdefault(name, {})["instance_url"] = st.text_input(
                            "Instance URL", value=creds.get("instance_url") or "", key=f"int_{name}_url"
                        )
                        new_local.setdefault(name, {})["username"] = st.text_input(
                            "Username", value=creds.get("username") or "", key=f"int_{name}_user"
                        )
                        new_local.setdefault(name, {})["password"] = st.text_input(
                            "Password", value=creds.get("password") or "", type="password", key=f"int_{name}_pw"
                        )
                    elif name == "jira":
                        new_local.setdefault(name, {})["base_url"] = st.text_input(
                            "Base URL", value=creds.get("base_url") or "", key=f"int_{name}_url"
                        )
                        new_local.setdefault(name, {})["username"] = st.text_input(
                            "Username (email)", value=creds.get("username") or "", key=f"int_{name}_user"
                        )
                        new_local.setdefault(name, {})["api_token"] = st.text_input(
                            "API token", value=creds.get("api_token") or "", type="password", key=f"int_{name}_token"
                        )
                        new_local.setdefault(name, {})["project_key"] = st.text_input(
                            "Project key (optional)", value=creds.get("project_key") or "", key=f"int_{name}_proj"
                        )

            if st.form_submit_button("Save integrations"):
                save_yaml(integrations_path, new_int)
                save_local_integrations(new_local)
                st.success("Saved integrations and credentials.")
                st.rerun()

# ---- RAG ----
with tab4:
    st.subheader("RAG (placeholder for when service is provided)")
    data = load_yaml(rag_path)

    if not st.session_state.config_edit_mode:
        for name, cfg in (data or {}).items():
            if isinstance(cfg, dict):
                with st.expander(name, expanded=True):
                    for k, v in cfg.items():
                        st.text(f"{k}: {v}")
        if not data:
            st.info("No RAG config.")
    else:
        with st.form("rag_form"):
            new_rag = {}
            for name, cfg in (data or {}).items():
                if not isinstance(cfg, dict):
                    continue
                with st.expander(name, expanded=True):
                    enabled = st.checkbox("enabled", value=bool(cfg.get("enabled", False)), key=f"rag_{name}_enabled")
                    new_rag[name] = {"enabled": enabled}
                    for k, v in cfg.items():
                        if k == "enabled":
                            continue
                        if isinstance(v, str):
                            val = st.text_input(k, value=v, key=f"rag_{name}_{k}")
                            new_rag[name][k] = val
                        else:
                            new_rag[name][k] = v

            if st.form_submit_button("Save to rag.yaml"):
                save_yaml(rag_path, new_rag)
                st.success("Saved rag.yaml")
                st.rerun()
