"""
app_streamlit.py — Interface web para o ADF Reprocess Agent.
Identidade visual SESI SENAI IEL.
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
    page_title="ADF Reprocess Agent · SESI SENAI IEL",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — Identidade visual SESI SENAI IEL
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Fundo geral ────────────────────────────────── */
    .stApp {
        background-color: #f4f6f9;
    }

    /* ── Sidebar ────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #1a2b4a !important;
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: #cbd8ec !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #2e4270 !important;
    }

    /* Logo topo da sidebar */
    .sidebar-logo {
        background: #142038;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 18px;
        border-bottom: 3px solid #0057a8;
    }
    .sidebar-logo .brand-main {
        font-size: 22px;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: 0.04em;
        line-height: 1;
    }
    .sidebar-logo .brand-main span {
        color: #4d9fec !important;
    }
    .sidebar-logo .brand-sub {
        font-size: 9px;
        color: #7a9ccb !important;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 2px;
    }
    .sidebar-logo .user-row {
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid #2e4270;
        font-size: 12px;
        color: #a0b8d8 !important;
    }
    .sidebar-logo .user-name {
        font-weight: 600;
        color: #e2ecf8 !important;
    }

    /* Status card na sidebar */
    .status-card {
        background: #142038;
        border-radius: 8px;
        padding: 11px 14px;
        margin-bottom: 8px;
        border-left: 3px solid #0057a8;
    }
    .status-card .s-label {
        font-size: 10px;
        color: #6a88b5 !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .status-card .s-value {
        font-size: 13px;
        color: #dce8f8 !important;
        font-weight: 500;
        margin-top: 1px;
    }

    /* Badges */
    .badge-ok {
        display: inline-block;
        background: #0a3d1f;
        color: #4ade80 !important;
        border: 1px solid #166534;
        border-radius: 20px;
        padding: 3px 14px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-warn {
        display: inline-block;
        background: #3d1a00;
        color: #fb923c !important;
        border: 1px solid #7c2d12;
        border-radius: 20px;
        padding: 3px 14px;
        font-size: 12px;
        font-weight: 600;
    }

    /* ── Área de chat ───────────────────────────────── */

    /* Header */
    .chat-header {
        background: #ffffff;
        border-radius: 10px;
        padding: 16px 22px;
        margin-bottom: 18px;
        border-bottom: 3px solid #0057a8;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .chat-header-left h1 {
        font-size: 20px;
        font-weight: 700;
        color: #1a2b4a;
        margin: 0;
    }
    .chat-header-left p {
        font-size: 12px;
        color: #6b7f99;
        margin: 2px 0 0 0;
    }
    .chat-header-right {
        font-size: 11px;
        color: #6b7f99;
        text-align: right;
    }
    .chat-header-right strong {
        color: #0057a8;
        display: block;
        font-size: 13px;
    }

    /* Mensagens */
    [data-testid="stChatMessage"] {
        background: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid #dce4ef !important;
        margin-bottom: 10px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }

    /* Expander de tool call */
    [data-testid="stExpander"] {
        background: #f0f4fb !important;
        border: 1px solid #c8d8ee !important;
        border-radius: 8px !important;
        margin: 6px 0 !important;
    }
    [data-testid="stExpander"] summary {
        color: #4a6fa5 !important;
        font-size: 12px !important;
        font-family: monospace !important;
    }

    /* Log de progresso */
    .progress-log {
        background: #e8eef7;
        border: 1px solid #c8d8ee;
        border-radius: 8px;
        padding: 10px 14px;
        font-family: monospace;
        font-size: 12px;
        color: #1a2b4a;
        max-height: 110px;
        overflow-y: auto;
        border-left: 3px solid #0057a8;
    }

    /* Botões sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background: #0057a8 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #0047880 !important;
        opacity: 0.9;
    }

    /* Rodapé SESI SENAI IEL */
    .footer-brand {
        margin-top: 18px;
        padding-top: 14px;
        border-top: 1px solid #2e4270;
        text-align: center;
    }
    .footer-brand .footer-text {
        font-size: 13px;
        font-weight: 700;
        color: #a0b8d8 !important;
        letter-spacing: 0.08em;
    }
    .footer-brand .footer-sub {
        font-size: 10px;
        color: #4f6a96 !important;
        margin-top: 2px;
    }

    /* Input de chat */
    [data-testid="stChatInput"] textarea {
        border: 1px solid #c8d8ee !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        color: #1a2b4a !important;
    }

    /* Avisos */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
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
        "chat_display": [],
        "agent_running": False,
        "agent_result": None,
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

    new_messages = st.session_state["messages"]
    new_boundaries = st.session_state["turn_boundaries"]

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

    st.session_state["messages"] = new_messages
    st.session_state["turn_boundaries"] = new_boundaries
    st.session_state["agent_result"] = {
        "text": text,
        "tool_calls": tool_calls_this_turn,
    }
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
        # Logo / marca
        st.markdown("""
        <div class="sidebar-logo">
            <div class="brand-main"><span>DATA</span> CG</div>
            <div class="brand-sub">Controle &amp; Gestão</div>
            <div class="user-row">
                <span class="user-name">ADF Reprocess Agent</span><br>
                Pipeline Orchestration
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Status de conexão
        cfg = get_config()
        factory   = cfg.get("factory_name", "")
        rg        = cfg.get("resource_group", "")
        api_key   = cfg.get("anthropic_api_key", "")
        sub       = cfg.get("subscription_id", "")

        if factory and sub and api_key:
            st.markdown('<span class="badge-ok">● Conectado</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="status-card">
                <div class="s-label">Factory</div>
                <div class="s-value">{factory}</div>
            </div>
            <div class="status-card">
                <div class="s-label">Resource Group</div>
                <div class="s-value">{rg or "—"}</div>
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

        st.markdown("""
        <div class="status-card">
            <div class="s-label">Modelo IA</div>
            <div class="s-value">Claude Haiku 4.5</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️  Limpar conversa", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["turn_boundaries"] = []
            st.session_state["chat_display"] = []
            st.session_state["stream_log"] = []
            st.rerun()

        # Rodapé SESI SENAI IEL
        st.markdown("""
        <div class="footer-brand">
            <div class="footer-text">SESI SENAI IEL</div>
            <div class="footer-sub">Sistema Indústria · Data Lake SGD</div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tool call expander
# ---------------------------------------------------------------------------
def _render_tool_call(tc: dict):
    icon = "✗" if tc["is_error"] else "✓"
    with st.expander(f"{icon}  `{tc['name']}`", expanded=False):
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

# Header
st.markdown("""
<div class="chat-header">
    <div class="chat-header-left">
        <h1>🔄 ADF Reprocess Agent</h1>
        <p>Orquestração de pipelines Azure Data Factory via linguagem natural</p>
    </div>
    <div class="chat-header-right">
        <strong>Data Lake SGD</strong>
        Tecnicos Data Lake · SESI SENAI IEL
    </div>
</div>
""", unsafe_allow_html=True)

# Histórico
for msg in st.session_state["chat_display"]:
    avatar = "🧑‍💻" if msg["role"] == "user" else "🔄"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["text"])
        for tc in msg.get("tool_calls", []):
            _render_tool_call(tc)

# Execução em andamento
if st.session_state["agent_running"]:
    with st.chat_message("assistant", avatar="🔄"):
        with st.spinner("Processando..."):
            logs = st.session_state["stream_log"]
            if logs:
                log_text = "<br>".join(f"› {l}" for l in logs[-8:])
                st.markdown(
                    f'<div class="progress-log">{log_text}</div>',
                    unsafe_allow_html=True,
                )
    time.sleep(0.8)
    st.rerun()

# Resultado pronto
if st.session_state["agent_result"] is not None:
    result = st.session_state["agent_result"]
    st.session_state["chat_display"].append({
        "role": "assistant",
        "text": result["text"],
        "tool_calls": result["tool_calls"],
    })
    st.session_state["agent_result"] = None
    st.rerun()

# Input
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
