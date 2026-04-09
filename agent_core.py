"""
agent_core.py — Lógica de orquestração reutilizável (sem input/print).
Usada pelo app_streamlit.py. O agent.py original permanece intocado.
"""
import json
import anthropic
from config import get_config
from tools import TOOLS, TOOL_FUNCTIONS

MODEL = "claude-haiku-4-5-20251001"
MAX_ITERATIONS = 10
MAX_HISTORY_TURNS = 5
MAX_TOOL_RESULT_CHARS = 2000

SYSTEM_PROMPT = """Agente de orquestração de pipelines Azure Data Factory (ADF) para reprocessamento histórico de meses.

Regras:
1. Mostre o plano (pipeline, ambiente, meses, parâmetros base sem closing) e peça confirmação antes de executar.
2. Execute apenas após "s", "sim" ou "yes". Qualquer outra resposta = aguardar esclarecimento.
3. Pedidos incompletos (sem pipeline, parâmetros ou ambiente) → pergunte antes de agir.
4. Se `aborted=True`: mostre o mês que falhou, a mensagem de erro e os meses concluídos. Oriente a reiniciar do mês falho.

Ferramentas:
- `reprocess_range`: meses contínuos com mesmos parâmetros base (só `closing` varia).
- `run_single`: meses não-contínuos ou com parâmetros distintos por mês. Chame uma vez por mês, sequencialmente. Polling é interno.

Notas:
- `user_parameters` é opaco — preserve integralmente. Só altere `closing` ao iterar meses.
- `final_parameters.closing` define o fim do range em `reprocess_range`.
- `env`: {"env": "dev"} ou {"env": "prod"}.
"""


def trim_history(messages: list[dict], turn_boundaries: list[int]) -> tuple[list[dict], list[int]]:
    if len(turn_boundaries) <= MAX_HISTORY_TURNS:
        return messages, turn_boundaries
    keep_from = turn_boundaries[-MAX_HISTORY_TURNS]
    trimmed = messages[keep_from:]
    new_boundaries = [i - keep_from for i in turn_boundaries[-MAX_HISTORY_TURNS:]]
    return trimmed, new_boundaries


def run_agent_turn(
    user_input: str,
    messages: list[dict],
    turn_boundaries: list[int],
    on_tool_call: callable = None,
    on_log: callable = None,
) -> tuple[str, list[dict], list[int]]:
    """
    Executa um turno completo: usuário → Claude → tools → ... → resposta final.

    Retorna (texto_resposta, messages_atualizado, turn_boundaries_atualizado).
    """
    cfg = get_config()
    if not cfg["anthropic_api_key"]:
        raise ValueError("ANTHROPIC_API_KEY não configurado no .env")

    def log(msg: str):
        if on_log:
            on_log(msg)

    client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])

    turn_boundaries = turn_boundaries + [len(messages)]
    messages = messages + [{"role": "user", "content": user_input}]

    response_text = ""

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages = messages + [{"role": "assistant", "content": response.content}]

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    response_text = block.text
            break

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                log(f"Executando `{tool_name}`...")

                if tool_name not in TOOL_FUNCTIONS:
                    tool_result = {"error": f"Ferramenta desconhecida: {tool_name}"}
                    is_error = True
                else:
                    try:
                        tool_result = TOOL_FUNCTIONS[tool_name](**tool_input)
                        is_error = "error" in tool_result
                        if is_error:
                            log(f"Erro em `{tool_name}`: {tool_result['error']}")
                        else:
                            log(f"`{tool_name}` concluído.")
                    except Exception as e:
                        tool_result = {"error": str(e)}
                        is_error = True
                        log(f"Exceção em `{tool_name}`: {e}")

                if on_tool_call:
                    on_tool_call(tool_name, tool_input, tool_result, is_error)

                result_str = json.dumps(tool_result, default=str)
                if len(result_str) > MAX_TOOL_RESULT_CHARS:
                    result_str = result_str[:MAX_TOOL_RESULT_CHARS] + "... [truncado]"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                    "is_error": is_error,
                })

            messages = messages + [{"role": "user", "content": tool_results}]
        else:
            log(f"stop_reason inesperado: {response.stop_reason}")
            break
    else:
        response_text = "Limite de iterações atingido."

    messages, turn_boundaries = trim_history(messages, turn_boundaries)
    return response_text, messages, turn_boundaries
