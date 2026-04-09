# ADF Reprocess Agent

Agente conversacional que orquestra reprocessamentos históricos em pipelines do **Azure Data Factory (ADF)** via Claude AI.

## Como funciona

Você descreve o que quer reprocessar em linguagem natural. O agente:

1. Mostra o plano (pipeline, ambiente, range de meses, parâmetros)
2. Aguarda sua confirmação antes de executar
3. Dispara os runs sequencialmente com polling automático
4. Em caso de falha, aborta e informa o mês exato que falhou

## Ferramentas disponíveis

| Ferramenta | Uso |
|---|---|
| `list_pipelines` | Lista todos os pipelines da factory |
| `reprocess_range` | Reprocessa um range contínuo de meses (mesmos parâmetros) |
| `run_single` | Executa 1 run por vez (meses não-contínuos ou parâmetros distintos) |

## Pré-requisitos

- Python 3.11+
- [Azure CLI](https://learn.microsoft.com/pt-br/cli/azure/install-azure-cli) instalado — **ou** credenciais de Service Principal

## Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repo>
cd adf-reprocess-agent

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o .env
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

## Configuração (.env)

Edite o arquivo `.env` com suas credenciais:

```env
ANTHROPIC_API_KEY=sk-ant-...

# Dados do seu Azure Data Factory
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_RESOURCE_GROUP=meu-resource-group
ADF_FACTORY_NAME=meu-data-factory
```

### Autenticação Azure

O agente tenta as duas formas automaticamente, nesta ordem:

**Opção 1 — Azure CLI (recomendada para uso local)**
```bash
az login
```
Sem nada adicional no `.env`.

**Opção 2 — Service Principal (recomendada para automação/CI)**
```env
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=seu-secret
```

### Parâmetros opcionais

```env
ADF_POLL_INTERVAL_SECONDS=15   # Intervalo entre verificações de status (padrão: 15s)
ADF_RUN_TIMEOUT_SECONDS=7200   # Timeout máximo por run (padrão: 2h)
```

## Uso

### Interface Web (recomendado)

```bash
streamlit run app_streamlit.py
```

Abre em `http://localhost:8501`. Interface de chat com histórico, feedback de progresso e visualização dos tool calls.

### Terminal (CLI)

```bash
python agent.py
```

### Exemplos de conversa

```
Você: reprocessa o pipeline PL_Fechamento de Jan/2024 até Mar/2024 em dev

Agente:
Pipeline: PL_Fechamento
Ambiente: DEV
Range: Jan/2024 → Mar/2024 (3 runs)
Parâmetros base: (nenhum parâmetro adicional)
Confirmar? (s/n):

Você: s

[1/3] Jan/2024 → disparando...
[1/3] Jan/2024 → ✓ Sucesso (142s)
[2/3] Fev/2024 → disparando...
...
```

```
Você: lista os pipelines disponíveis

Você: qual foi o último run do pipeline PL_Carga?

Você: sair
```

## Estrutura do projeto

```
adf-reprocess-agent/
├── app_streamlit.py  # Interface web (Streamlit)
├── agent_core.py     # Lógica de orquestração reutilizável
├── agent.py          # Loop conversacional CLI (REPL)
├── adf_client.py     # Wrapper da ADF REST API
├── config.py         # Leitura de .env + autenticação Azure
├── requirements.txt  # Dependências Python
├── .env.example      # Template de configuração
└── tools/
    ├── __init__.py   # Registry de ferramentas para o Claude
    └── adf_tools.py  # Implementação das ferramentas
```

## Dependências

| Pacote | Uso |
|---|---|
| `anthropic` | SDK Claude AI |
| `python-dotenv` | Leitura do `.env` |
| `msal` | Autenticação Service Principal Azure |
| `requests` | Chamadas REST à API do ADF |
| `python-dateutil` | Iteração sobre range de meses |
| `streamlit` | Interface web |
