"""
tools/__init__.py — Registry de ferramentas ADF
"""
from tools.adf_tools import (
    list_pipelines,
    run_single,
    reprocess_range,
)

TOOL_FUNCTIONS = {
    "list_pipelines": list_pipelines,
    "run_single": run_single,
    "reprocess_range": reprocess_range,
}

TOOLS = [
    {
        "name": "list_pipelines",
        "description": "Lista todos os pipelines da ADF factory.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "run_single",
        "description": (
            "Dispara 1 run e aguarda conclusão internamente (polling sem chamar a API Claude). "
            "Use este quando os meses são não-contínuos ou têm parâmetros diferentes entre si. "
            "Chame uma vez por mês, sequencialmente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_name": {
                    "type": "string",
                    "description": "Nome do pipeline no ADF.",
                },
                "user_parameters": {
                    "type": "object",
                    "description": "Parâmetros completos do run (opaco). Deve conter closing.year e closing.month.",
                },
                "env": {
                    "type": "object",
                    "description": "Ambiente de execução.",
                    "properties": {
                        "env": {
                            "type": "string",
                            "enum": ["dev", "prod"],
                            "description": "Ambiente: 'dev' ou 'prod'.",
                        },
                    },
                    "required": ["env"],
                },
            },
            "required": ["pipeline_name", "user_parameters", "env"],
        },
    },
    {
        "name": "reprocess_range",
        "description": (
            "Orquestrador principal: reprocessa um range de meses sequencialmente. "
            "Apresenta o plano e executa run a run. "
            "Em caso de falha, cancela imediatamente e retorna aborted=True com detalhes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_name": {
                    "type": "string",
                    "description": "Nome do pipeline no ADF.",
                },
                "user_parameters": {
                    "type": "object",
                    "description": (
                        "Parâmetros completos do primeiro run (opaco). "
                        "Deve conter closing.year e closing.month para definir o início do range. "
                        "Todo o restante é passado intacto ao ADF."
                    ),
                },
                "final_parameters": {
                    "type": "object",
                    "description": "Define o fim do range de reprocessamento.",
                    "properties": {
                        "closing": {
                            "type": "object",
                            "properties": {
                                "year": {"type": "string", "description": "Ano final (ex: '2025')."},
                                "month": {"type": "string", "description": "Mês final (ex: '8')."},
                            },
                            "required": ["year", "month"],
                        },
                    },
                    "required": ["closing"],
                },
                "env": {
                    "type": "object",
                    "description": "Ambiente de execução.",
                    "properties": {
                        "env": {
                            "type": "string",
                            "enum": ["dev", "prod"],
                            "description": "Ambiente: 'dev' ou 'prod'.",
                        },
                    },
                    "required": ["env"],
                },
            },
            "required": ["pipeline_name", "user_parameters", "final_parameters", "env"],
        },
    },
]
