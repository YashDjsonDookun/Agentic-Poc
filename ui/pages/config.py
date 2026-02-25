"""
Configuration: view and edit YAML config from the UI.
Read-only by default; toggle edit mode to change values and save back to config files.
No secrets in UI — only structure and env var names (values stay in .env).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import yaml
from shared.config_loader import CONFIG_DIR, get_env, get_services_config, get_integrations_config

st.title("Configuration")
st.caption("View and edit config. Secrets stay in .env — only structure and env var names here.")

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

    if not st.session_state.config_edit_mode:
        st.markdown(f"- **Jira**: {'✅ configured' if jira.is_configured() else '❌ not configured'}")
        st.markdown(f"- **ServiceNow**: {'✅ configured' if servicenow.is_configured() else '❌ not configured'}")
        for name, cfg in (data or {}).items():
            if isinstance(cfg, dict):
                with st.expander(name, expanded=False):
                    st.text(f"Enabled: {cfg.get('enabled', False)}")
                    for k, v in cfg.items():
                        if k != "enabled" and isinstance(v, str):
                            st.text(f"{k}: {v}")
        if not data:
            st.info("No integrations in config.")
    else:
        with st.form("integrations_form"):
            new_int = {}
            for name, cfg in (data or {}).items():
                if not isinstance(cfg, dict):
                    continue
                with st.expander(name, expanded=False):
                    enabled = st.checkbox("Enabled", value=bool(cfg.get("enabled", False)), key=f"int_{name}_enabled")
                    new_int[name] = {"enabled": enabled}
                    for k, v in cfg.items():
                        if k == "enabled":
                            continue
                        if isinstance(v, str):
                            val = st.text_input(k, value=v, key=f"int_{name}_{k}")
                            new_int[name][k] = val
                        else:
                            new_int[name][k] = v

            if st.form_submit_button("Save to integrations.yaml"):
                save_yaml(integrations_path, new_int)
                st.success("Saved integrations.yaml")
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
