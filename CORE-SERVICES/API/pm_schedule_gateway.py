from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

CREATE_PATH = "ltsa/pm-schedule/create"
DETAIL_PATH = "ltsa/pm-schedule/detail"
LIST_PATH = "ltsa/pm-schedule/list"
UPDATE_PATH = "ltsa/pm-schedule/update"
DELETE_PATH = "ltsa/pm-schedule/delete"


@dataclass(slots=True)
class PMScheduleGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class PMScheduleGateway:
    """Transport layer only: forwards requests to the existing canonical PM
    Schedule n8n workflows and returns their responses unchanged. No
    business logic, no persistence, no registry, no runtime. Identical
    shape to WorkOrderGateway/MaintenanceHistoryGateway/PumpGateway, per
    ADR-PM-001's Required Backend Changes.
    """

    def __init__(self, config: PMScheduleGatewayConfig | None = None):
        self.config = config or PMScheduleGatewayConfig(
            base_url=os.getenv("AI5R_PM_SCHEDULE_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def create_pm_schedule(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", CREATE_PATH, body=payload)

    def get_pm_schedule(self, pm_schedule_code: str) -> dict[str, Any]:
        return self._call("GET", DETAIL_PATH, query={"pm_schedule_code": pm_schedule_code})

    def list_pm_schedules(self) -> dict[str, Any]:
        return self._call("GET", LIST_PATH)

    def update_pm_schedule(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("PUT", UPDATE_PATH, body=payload)

    def delete_pm_schedule(self, pm_schedule_code: str) -> dict[str, Any]:
        return self._call("DELETE", DELETE_PATH, query={"pm_schedule_code": pm_schedule_code})

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
