"""
agent.py — Loop conversacional ADF Reprocessing Agent
"""
import json
import anthropic
from config import get_config
from tools import TOOLS, TOOL_FUNCTIONS

MAX_ITERATIONS = 10
MAX_HISTORY_TURNS = 5       # turnos completos mantidos no histórico
MAX_TOOL_RESULT_CHARS = 2000  # trunca tool results grandes antes de gravar
MODEL = "claude-haiku-4-5-20251001"

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


def _format_plan(
    pipeline_name: str,
    env: dict,
    user_parameters: dict,
    final_parameters: dict,
) -> str:
    """Formata o plano de reprocessamento para exibição."""
    from dateutil.relativedelta import relativedelta
    from datetime import date

    MONTH_PT = [
        "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez",
    ]

    try:
        start = user_parameters["closing"]
        fy, fm = int(start["year"]), int(start["month"])
        end = final_parameters["closing"]
        ty, tm = int(end["year"]), int(end["month"])

        months = []
        current = date(fy, fm, 1)
        end_date = date(ty, tm, 1)
        while current <= end_date:
            months.append((current.year, current.month))
            current += relativedelta(months=1)

        n = len(months)
        start_label = f"{MONTH_PT[fm]}/{fy}"
        end_label = f"{MONTH_PT[tm]}/{ty}"
        range_str = f"{start_label} → {end_label} ({n} run{'s' if n != 1 else ''})"
    except Exception:
        range_str = "(não foi possível calcular o range)"

    env_str = env.get("env", "?").upper()

    # Resumo dos parâmetros base (exclui 'closing')
    base = {k: v for k, v in user_parameters.items() if k != "closing"}
    if base:
        params_str = ", ".join(f"{k}={json.dumps(v)}" for k, v in base.items())
    else:
        params_str = "(nenhum parâmetro adicional)"

    return (
        f"Pipeline: {pipeline_name}\n"
        f"Ambiente: {env_str}\n"
        f"Range: {range_str}\n"
        f"Parâmetros base: {params_str}\n"
        f"Confirmar? (s/n):"
    )


def _trim_history(messages: list[dict], turn_boundaries: list[int]) -> tuple[list[dict], list[int]]:
    """Remove turnos antigos se exceder MAX_HISTORY_TURNS."""
    if len(turn_boundaries) <= MAX_HISTORY_TURNS:
        return messages, turn_boundaries
    keep_from = turn_boundaries[-MAX_HISTORY_TURNS]
    trimmed = messages[keep_from:]
    new_boundaries = [i - keep_from for i in turn_boundaries[-MAX_HISTORY_TURNS:]]
    return trimmed, new_boundaries


def chat_loop() -> None:
    """REPL conversacional — mantém histórico entre turnos."""
    cfg = get_config()
    if not cfg["anthropic_api_key"]:
        raise ValueError("ANTHROPIC_API_KEY não configurado no .env")

    client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])
    messages: list[dict] = []
    turn_boundaries: list[int] = []  # índice em messages onde cada turno começa

    print("ADF Reprocessing Agent — digite 'sair' para encerrar.\n")

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break

        turn_boundaries.append(len(messages))
        messages.append({"role": "user", "content": user_input})

        for iteration in range(MAX_ITERATIONS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        print(f"\nAgente: {block.text}\n")
                break

            if response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    print(f"\n[Tool] {tool_name}({json.dumps(tool_input, default=str)[:300]})")

                    if tool_name not in TOOL_FUNCTIONS:
                        tool_result = {"error": f"Ferramenta desconhecida: {tool_name}"}
                        is_error = True
                    else:
                        try:
                            tool_result = TOOL_FUNCTIONS[tool_name](**tool_input)
                            is_error = "error" in tool_result
                            if not is_error:
                                preview = json.dumps(tool_result, default=str)[:400]
                                print(f"[Tool] OK: {preview}...")
                            else:
                                print(f"[Tool] Erro: {tool_result['error']}")
                        except Exception as e:
                            tool_result = {"error": str(e)}
                            is_error = True
                            print(f"[Tool] Exceção: {e}")

                    result_str = json.dumps(tool_result, default=str)
                    if len(result_str) > MAX_TOOL_RESULT_CHARS:
                        result_str = result_str[:MAX_TOOL_RESULT_CHARS] + "... [truncado]"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                        "is_error": is_error,
                    })

                messages.append({"role": "user", "content": tool_results})
            else:
                print(f"[Agent] stop_reason inesperado: {response.stop_reason}")
                break
        else:
            print("[Agent] Limite de iterações atingido.")

        # Descarta turnos antigos após completar o turno atual
        messages, turn_boundaries = _trim_history(messages, turn_boundaries)


if __name__ == "__main__":
    chat_loop()
