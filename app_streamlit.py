"""
app_streamlit.py — Interface web para o ADF Reprocess Agent.
Rodar: streamlit run app_streamlit.py
"""
import time
import threading
import json
import streamlit as st
from config import get_config
from agent_core import run_agent_turn

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ADF Reprocess Agent",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS customizado
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Fundo geral */
    .stApp { background-color: #0f1117; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b27;
        border-right: 1px solid #1e2535;
    }

    /* Status card */
    .status-card {
        background: #1e2535;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
        border: 1px solid #2a3550;
    }
    .status-card .label {
        font-size: 11px;
        color: #7a8aaa;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 2px;
    }
    .status-card .value {
        font-size: 14px;
        color: #e2e8f0;
        font-weight: 500;
    }
    .badge-ok {
        display: inline-block;
        background: #14532d;
        color: #4ade80;
        border: 1px solid #166534;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-warn {
        display: inline-block;
        background: #422006;
        color: #fb923c;
        border: 1px solid #7c2d12;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 12px;
        font-weight: 600;
    }

    /* Header da área de chat */
    .chat-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 20px 0 10px 0;
        border-bottom: 1px solid #1e2535;
        margin-bottom: 20px;
    }
    .chat-header h1 {
        font-size: 22px;
        font-weight: 700;
        color: #e2e8f0;
        margin: 0;
    }
    .chat-header .subtitle {
        font-size: 13px;
        color: #7a8aaa;
        margin: 0;
    }

    /* Mensagem do agente */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
    }

    /* Tool call expander */
    [data-testid="stExpander"] {
        background: #161b27 !important;
        border: 1px solid #1e2535 !important;
        border-radius: 8px !important;
        margin: 6px 0 !important;
    }
    [data-testid="stExpander"] summary {
        color: #7a8aaa !important;
        font-size: 12px !important;
        font-family: monospace !important;
    }

    /* Log de progresso */
    .progress-log {
        background: #0a0e18;
        border: 1px solid #1e2535;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: monospace;
        font-size: 12px;
        color: #4ade80;
        max-height: 120px;
        overflow-y: auto;
    }

    /* Input */
    [data-testid="stChatInput"] {
        border-top: 1px solid #1e2535 !important;
    }

    /* Botão primário */
    .stButton > button {
        background: #1d4ed8;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 500;
    }
    .stButton > button:hover {
        background: #2563eb;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init():
    defaults = {
        "messages": [],
        "turn_boundaries": [],
        "chat_display": [],   # [{role, text, tool_calls:[{name,input,result,is_error}]}]
        "agent_running": False,
        "agent_result": None,  # {text, tool_calls} quando thread termina
        "stream_log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ---------------------------------------------------------------------------
# Thread worker
# ---------------------------------------------------------------------------
def _thread_run(user_input: str):
    tool_calls_this_turn = []

    def on_tool_call(name, inp, result, is_error):
        tool_calls_this_turn.append({
            "name": name,
            "input": inp,
            "result": result,
            "is_error": is_error,
        })

    def on_log(msg: str):
        st.session_state["stream_log"].append(msg)

    try:
        text, new_messages, new_boundaries = run_agent_turn(
            user_input=user_input,
            messages=st.session_state["messages"],
            turn_boundaries=st.session_state["turn_boundaries"],
            on_tool_call=on_tool_call,
            on_log=on_log,
        )
    except Exception as e:
        text = f"Erro ao processar: {e}"

    st.session_state["agent_result"] = {
        "text": text,
        "tool_calls": tool_calls_this_turn,
    }
    st.session_state["messages"] = new_messages if "new_messages" in dir() else st.session_state["messages"]
    st.session_state["turn_boundaries"] = new_boundaries if "new_boundaries" in dir() else st.session_state["turn_boundaries"]
    st.session_state["agent_running"] = False


def _start_agent(user_input: str):
    st.session_state["stream_log"] = []
    st.session_state["agent_running"] = True
    st.session_state["agent_result"] = None
    t = threading.Thread(target=_thread_run, args=(user_input,), daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def _render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ ADF Reprocess Agent")
        st.markdown("---")

        cfg = get_config()
        factory = cfg.get("factory_name", "")
        rg = cfg.get("resource_group", "")
        sub = cfg.get("subscription_id", "")
        api_key = cfg.get("anthropic_api_key", "")

        if factory and sub and api_key:
            st.markdown('<span class="badge-ok">● Conectado</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="status-card">
                <div class="label">Factory</div>
                <div class="value">{factory}</div>
            </div>
            <div class="status-card">
                <div class="label">Resource Group</div>
                <div class="value">{rg or "—"}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-warn">⚠ .env incompleto</span>', unsafe_allow_html=True)
            missing = []
            if not api_key:
                missing.append("ANTHROPIC_API_KEY")
            if not sub:
                missing.append("AZURE_SUBSCRIPTION_ID")
            if not factory:
                missing.append("ADF_FACTORY_NAME")
            st.caption(f"Faltando: {', '.join(missing)}")
            st.caption("Configure o arquivo `.env` conforme `.env.example`.")

        st.markdown("---")
        st.markdown("**Modelo**")
        st.caption("claude-haiku-4-5")

        st.markdown("---")
        if st.button("🗑 Limpar conversa", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["turn_boundaries"] = []
            st.session_state["chat_display"] = []
            st.session_state["stream_log"] = []
            st.rerun()

        st.markdown("---")
        st.caption("ADF Reprocess Agent · branch dev")


# ---------------------------------------------------------------------------
# Renderiza tool call como expander
# ---------------------------------------------------------------------------
def _render_tool_call(tc: dict):
    icon = "✗" if tc["is_error"] else "✓"
    label = f"{icon} `{tc['name']}`"
    with st.expander(label, expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Input")
            st.json(tc["input"])
        with col2:
            st.caption("Output")
            if tc["is_error"]:
                st.error(json.dumps(tc["result"], default=str, ensure_ascii=False))
            else:
                st.json(tc["result"])


# ---------------------------------------------------------------------------
# Layout principal
# ---------------------------------------------------------------------------
_render_sidebar()

st.markdown("""
<div class="chat-header">
    <div>
        <h1>ADF Reprocess Agent</h1>
        <p class="subtitle">Orquestração de pipelines Azure Data Factory via linguagem natural</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Histórico de mensagens
for msg in st.session_state["chat_display"]:
    avatar = "🧑‍💻" if msg["role"] == "user" else "⚙️"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["text"])
        for tc in msg.get("tool_calls", []):
            _render_tool_call(tc)

# Execução em andamento
if st.session_state["agent_running"]:
    with st.chat_message("assistant", avatar="⚙️"):
        with st.spinner("Processando..."):
            log_placeholder = st.empty()
            logs = st.session_state["stream_log"]
            if logs:
                log_text = "\n".join(f"› {l}" for l in logs[-8:])
                log_placeholder.markdown(
                    f'<div class="progress-log">{log_text}</div>',
                    unsafe_allow_html=True,
                )
    time.sleep(0.8)
    st.rerun()

# Processa resultado quando thread termina
if st.session_state["agent_result"] is not None:
    result = st.session_state["agent_result"]
    st.session_state["chat_display"].append({
        "role": "assistant",
        "text": result["text"],
        "tool_calls": result["tool_calls"],
    })
    st.session_state["agent_result"] = None
    st.rerun()

# Input do usuário
if prompt := st.chat_input("Ex: reprocessa o pipeline PL_Fechamento de Jan/2024 até Mar/2024 em dev"):
    if st.session_state["agent_running"]:
        st.warning("Aguarde o agente terminar antes de enviar uma nova mensagem.")
    else:
        st.session_state["chat_display"].append({
            "role": "user",
            "text": prompt,
            "tool_calls": [],
        })
        _start_agent(prompt)
        st.rerun()
