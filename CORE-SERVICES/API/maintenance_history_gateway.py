from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

CREATE_PATH = "ltsa/maintenance-history/create"
DETAIL_PATH = "ltsa/maintenance-history/detail"
LIST_PATH = "ltsa/maintenance-history/list"
UPDATE_PATH = "ltsa/maintenance-history/update"
DELETE_PATH = "ltsa/maintenance-history/delete"


@dataclass(slots=True)
class MaintenanceHistoryGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class MaintenanceHistoryGateway:
    """Transport layer only: forwards requests to the existing canonical
    Maintenance History n8n workflows and returns their responses unchanged.
    No business logic, no persistence, no registry, no runtime.
    """

    def __init__(self, config: MaintenanceHistoryGatewayConfig | None = None):
        self.config = config or MaintenanceHistoryGatewayConfig(
            base_url=os.getenv("AI5R_MAINTENANCE_HISTORY_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def create_maintenance_history(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", CREATE_PATH, body=payload)

    def get_maintenance_history(self, maintenance_record_code: str) -> dict[str, Any]:
        return self._call(
            "GET", DETAIL_PATH, query={"maintenance_record_code": maintenance_record_code}
        )

    def list_maintenance_history(self) -> dict[str, Any]:
        return self._call("GET", LIST_PATH)

    def update_maintenance_history(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("PUT", UPDATE_PATH, body=payload)

    def delete_maintenance_history(self, maintenance_record_code: str) -> dict[str, Any]:
        return self._call(
            "DELETE", DELETE_PATH, query={"maintenance_record_code": maintenance_record_code}
        )

    def _call(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path}"

        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}

        request = urllib.request.Request(url, data=data, method=method, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8")

        return json.loads(raw)
