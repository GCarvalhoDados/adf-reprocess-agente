"""
adf_client.py — Wrapper REST da ADF API
"""
import time
import requests
from datetime import datetime, timedelta
from config import get_azure_token, get_config

API_VERSION = "2018-06-01"
BASE = "https://management.azure.com"


class ADFClient:
    def __init__(self):
        cfg = get_config()
        self.sub = cfg["subscription_id"]
        self.rg = cfg["resource_group"]
        self.factory = cfg["factory_name"]
        self.poll_interval = cfg["poll_interval"]
        self.run_timeout = cfg["run_timeout"]

    def _base(self) -> str:
        return (
            f"{BASE}/subscriptions/{self.sub}"
            f"/resourceGroups/{self.rg}"
            f"/providers/Microsoft.DataFactory/factories/{self.factory}"
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {get_azure_token()}",
            "Content-Type": "application/json",
        }

    def _get(self, url: str) -> dict:
        r = requests.get(url, headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, url: str, body: dict) -> dict:
        r = requests.post(url, headers=self._headers(), json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def list_pipelines(self) -> list[dict]:
        url = f"{self._base()}/pipelines?api-version={API_VERSION}"
        data = self._get(url)
        result = [
            {
                "name": p["name"],
                "description": p.get("properties", {}).get("description", ""),
            }
            for p in data.get("value", [])
        ]
        while "nextLink" in data:
            data = self._get(data["nextLink"])
            result += [
                {
                    "name": p["name"],
                    "description": p.get("properties", {}).get("description", ""),
                }
                for p in data.get("value", [])
            ]
        return result

    def get_pipeline_info(self, name: str) -> dict:
        return self._get(f"{self._base()}/pipelines/{name}?api-version={API_VERSION}")

    def trigger_run(self, pipeline: str, params: dict) -> str:
        data = self._post(
            f"{self._base()}/pipelines/{pipeline}/createRun?api-version={API_VERSION}",
            params,
        )
        return data["runId"]

    def get_run_status(self, run_id: str) -> dict:
        data = self._get(f"{self._base()}/pipelineruns/{run_id}?api-version={API_VERSION}")
        start, end = data.get("runStart"), data.get("runEnd")
        duration = None
        if start and end:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
                duration = int(
                    (
                        datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
                    ).total_seconds()
                )
            except ValueError:
                pass
        return {
            "run_id": run_id,
            "status": data.get("status", "Unknown"),
            "start_time": start,
            "end_time": end,
            "duration_seconds": duration,
            "message": data.get("message", ""),
        }

    def list_recent_runs(self, pipeline: str, last_n: int = 20) -> list[dict]:
        url = f"{self._base()}/queryPipelineRuns?api-version={API_VERSION}"
        body = {
            "lastUpdatedAfter": (datetime.utcnow() - timedelta(days=365)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "lastUpdatedBefore": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "filters": [
                {"operand": "PipelineName", "operator": "Equals", "values": [pipeline]}
            ],
            "orderBy": [{"orderBy": "RunStart", "order": "DESC"}],
        }
        return [
            {
                "run_id": r.get("runId"),
                "status": r.get("status"),
                "start_time": r.get("runStart"),
                "parameters": r.get("parameters", {}),
            }
            for r in self._post(url, body).get("value", [])[:last_n]
        ]

    def poll_until_done(self, run_id: str, on_progress=None) -> dict:
        deadline = time.time() + self.run_timeout
        while time.time() < deadline:
            s = self.get_run_status(run_id)
            if on_progress:
                on_progress(s)
            if s["status"] in {"Succeeded", "Failed", "Cancelled"}:
                return s
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Run {run_id} não finalizou em {self.run_timeout}s")
