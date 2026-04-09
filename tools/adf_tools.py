"""
tools/adf_tools.py — Implementação das 6 ferramentas ADF
"""
from __future__ import annotations

import sys
from dateutil.relativedelta import relativedelta
from datetime import date

from adf_client import ADFClient

MONTH_PT = [
    "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def list_pipelines() -> dict:
    """Lista todos os pipelines da factory."""
    try:
        client = ADFClient()
        pipelines = client.list_pipelines()
        return {"pipelines": pipelines, "count": len(pipelines)}
    except Exception as e:
        return {"error": str(e)}


def get_pipeline_info(pipeline_name: str) -> dict:
    """Retorna detalhes e schema de parâmetros de um pipeline."""
    try:
        client = ADFClient()
        info = client.get_pipeline_info(pipeline_name)
        props = info.get("properties", {})
        parameters = props.get("parameters", {})
        return {
            "name": info.get("name"),
            "description": props.get("description", ""),
            "parameters": parameters,
            "activities_count": len(props.get("activities", [])),
        }
    except Exception as e:
        return {"error": str(e)}


def list_recent_runs(pipeline_name: str, last_n: int = 20) -> dict:
    """Retorna os últimos N runs do pipeline."""
    try:
        client = ADFClient()
        runs = client.list_recent_runs(pipeline_name, last_n)
        return {"pipeline": pipeline_name, "runs": runs, "count": len(runs)}
    except Exception as e:
        return {"error": str(e)}


def trigger_run(pipeline_name: str, parameters: dict) -> dict:
    """Dispara 1 run e retorna o run_id imediatamente (fire-and-check)."""
    try:
        client = ADFClient()
        run_id = client.trigger_run(pipeline_name, parameters)
        return {"run_id": run_id, "pipeline": pipeline_name, "parameters": parameters}
    except Exception as e:
        return {"error": str(e)}


def get_run_status(run_id: str) -> dict:
    """Retorna status atual de um run: InProgress | Succeeded | Failed | Cancelled."""
    try:
        client = ADFClient()
        return client.get_run_status(run_id)
    except Exception as e:
        return {"error": str(e)}


def run_single(
    pipeline_name: str,
    user_parameters: dict,
    env,
) -> dict:
    """
    Dispara 1 run e aguarda conclusão internamente (sem polling via Claude).
    Retorna o resultado final: succeeded=True/False + detalhes.

    user_parameters: parâmetros completos do run (opaco).
    env: {"env": "dev"} ou {"env": "prod"} — ou string "dev"/"prod".
    """
    # Normaliza env: o ADF espera {"env": "prod"}, não "prod"
    if isinstance(env, str):
        env = {"env": env}

    try:
        client = ADFClient()
    except Exception as e:
        return {"error": str(e)}

    params = {"user_parameters": user_parameters, "env": env}
    label = user_parameters.get("closing", {})
    month = label.get("month", "?")
    year = label.get("year", "?")
    label_str = f"{MONTH_PT[int(month)] if str(month).isdigit() else month}/{year}"

    print(f"\n[run_single] {label_str} → disparando...", flush=True)

    try:
        run_id = client.trigger_run(pipeline_name, params)
    except Exception as e:
        return {"succeeded": False, "error_message": f"Falha ao disparar: {e}", "run_id": None}

    print(f"[run_single] {label_str} → run_id: {run_id}", flush=True)

    def _progress(s: dict) -> None:
        dur = s.get("duration_seconds")
        print(f"[run_single] {label_str} → {s['status']}{f' ({dur}s)' if dur else ''}", end="\r", flush=True)

    try:
        result = client.poll_until_done(run_id, on_progress=_progress)
    except TimeoutError as te:
        print(flush=True)
        return {"succeeded": False, "error_message": str(te), "run_id": run_id}

    print(flush=True)
    status = result.get("status", "Unknown")
    dur = result.get("duration_seconds")

    if status == "Succeeded":
        print(f"[run_single] {label_str} → ✓ Sucesso{f' ({dur}s)' if dur else ''}", flush=True)
        return {"succeeded": True, "run_id": run_id, "duration_seconds": dur, "month": label_str}
    else:
        msg = result.get("message", "")
        print(f"[run_single] {label_str} → ✗ {status}: {msg}", flush=True)
        return {"succeeded": False, "run_id": run_id, "status": status, "error_message": msg, "month": label_str}


def reprocess_range(
    pipeline_name: str,
    user_parameters: dict,
    final_parameters: dict,
    env,
) -> dict:
    """
    Orquestrador principal: reprocessa um range de meses sequencialmente.

    Loop: trigger → poll_until_done → avalia resultado.
    Em falha: cancela imediatamente, retorna aborted=True com detalhes do erro.
    Nunca levanta exceção — retorna dict com resultado.

    user_parameters: JSON completo do 1º run (opaco); extrai closing.year/month para início.
    final_parameters: {"closing": {"year": "...", "month": "..."}} — define o fim do range.
    env: {"env": "dev"} ou {"env": "prod"} — ou string "dev"/"prod".
    """
    # Normaliza env: o ADF espera {"env": "prod"}, não "prod"
    if isinstance(env, str):
        env = {"env": env}
    try:
        client = ADFClient()
    except Exception as e:
        return {"error": str(e)}

    # Extrai início do range a partir de user_parameters.closing
    try:
        start_closing = user_parameters["closing"]
        from_year = int(start_closing["year"])
        from_month = int(start_closing["month"])
    except (KeyError, TypeError, ValueError) as e:
        return {"error": f"Não foi possível extrair closing.year/month de user_parameters: {e}"}

    # Extrai fim do range a partir de final_parameters.closing
    try:
        end_closing = final_parameters["closing"]
        to_year = int(end_closing["year"])
        to_month = int(end_closing["month"])
    except (KeyError, TypeError, ValueError) as e:
        return {"error": f"Não foi possível extrair closing.year/month de final_parameters: {e}"}

    # Gera lista de meses
    months: list[tuple[int, int]] = []
    current = date(from_year, from_month, 1)
    end_date = date(to_year, to_month, 1)
    while current <= end_date:
        months.append((current.year, current.month))
        current += relativedelta(months=1)

    if not months:
        return {"error": "Range inválido: data inicial é posterior à data final."}

    total = len(months)
    succeeded: list[str] = []

    print(f"\n[ADF] Iniciando reprocessamento: {total} meses", flush=True)
    print(f"[ADF] Pipeline: {pipeline_name}", flush=True)

    for idx, (year, month) in enumerate(months, start=1):
        label = f"{MONTH_PT[month]}/{year}"
        params = {
            "user_parameters": {
                **user_parameters,
                "closing": {"year": str(year), "month": str(month)},
            },
            "env": env,
        }

        print(f"\n[{idx}/{total}] {label} → disparando...", flush=True)

        try:
            run_id = client.trigger_run(pipeline_name, params)
        except Exception as e:
            return {
                "aborted": True,
                "failed_month": label,
                "completed_months": succeeded,
                "error_message": f"Falha ao disparar run: {e}",
                "run_id": None,
            }

        print(f"[{idx}/{total}] {label} → disparado (run_id: {run_id})", flush=True)

        def _print_progress(s: dict, _idx=idx, _total=total, _label=label) -> None:
            dur = s.get("duration_seconds")
            dur_str = f" ({dur}s)" if dur else ""
            print(
                f"[{_idx}/{_total}] {_label} → {s['status']}{dur_str}",
                end="\r",
                flush=True,
            )

        try:
            result = client.poll_until_done(run_id, on_progress=_print_progress)
        except TimeoutError as te:
            print(flush=True)
            return {
                "aborted": True,
                "failed_month": label,
                "completed_months": succeeded,
                "error_message": str(te),
                "run_id": run_id,
            }

        print(flush=True)  # newline após \r
        status = result.get("status", "Unknown")
        dur = result.get("duration_seconds")
        dur_str = f" ({dur}s)" if dur else ""

        if status == "Succeeded":
            print(f"[{idx}/{total}] {label} → ✓ Sucesso{dur_str}", flush=True)
            succeeded.append(label)
        else:
            msg = result.get("message", "")
            print(f"[{idx}/{total}] {label} → ✗ {status}: {msg}", flush=True)
            return {
                "aborted": True,
                "failed_month": label,
                "completed_months": succeeded,
                "error_message": msg,
                "run_id": run_id,
            }

    print(f"\n[ADF] Concluído: {total}/{total} com sucesso.", flush=True)
    return {
        "aborted": False,
        "total": total,
        "succeeded_months": succeeded,
    }
