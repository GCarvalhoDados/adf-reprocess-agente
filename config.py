"""
config.py — Lê .env + detecta auth (az CLI → Service Principal)
"""
import json
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _try_azure_cli() -> str | None:
    try:
        r = subprocess.run(
            ["az", "account", "get-access-token", "--resource", "https://management.azure.com"],
            capture_output=True, text=True, timeout=15, shell=True
        )
        if r.returncode == 0:
            return json.loads(r.stdout)["accessToken"]
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def _try_service_principal() -> str | None:
    import msal
    t = os.getenv("AZURE_TENANT_ID", "")
    c = os.getenv("AZURE_CLIENT_ID", "")
    s = os.getenv("AZURE_CLIENT_SECRET", "")
    if not all([t, c, s]):
        return None
    app = msal.ConfidentialClientApplication(
        c,
        authority=f"https://login.microsoftonline.com/{t}",
        client_credential=s,
    )
    result = app.acquire_token_for_client(scopes=["https://management.azure.com/.default"])
    return result.get("access_token")


def get_azure_token() -> str:
    """Obtém token Azure. Chamado a cada request (tokens CLI expiram em ~60min)."""
    token = _try_azure_cli() or _try_service_principal()
    if not token:
        raise RuntimeError(
            "Auth falhou. Execute 'az login' ou configure Service Principal no .env"
        )
    return token


def get_config() -> dict:
    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "subscription_id":   os.getenv("AZURE_SUBSCRIPTION_ID", ""),
        "resource_group":    os.getenv("AZURE_RESOURCE_GROUP", ""),
        "factory_name":      os.getenv("ADF_FACTORY_NAME", ""),
        "poll_interval":     int(os.getenv("ADF_POLL_INTERVAL_SECONDS", "15")),
        "run_timeout":       int(os.getenv("ADF_RUN_TIMEOUT_SECONDS", "7200")),
    }


if __name__ == "__main__":
    cfg = get_config()
    import json as _json
    print(_json.dumps({k: v for k, v in cfg.items() if k != "anthropic_api_key"}, indent=2))
    print(f"anthropic_api_key: {'set' if cfg['anthropic_api_key'] else 'NOT SET'}")
