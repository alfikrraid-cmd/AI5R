from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

CREATE_PATH = "ltsa/cm-report/create"
DETAIL_PATH = "ltsa/cm-report/detail"
LIST_PATH = "ltsa/cm-report/list"
UPDATE_PATH = "ltsa/cm-report/update"
DELETE_PATH = "ltsa/cm-report/delete"


@dataclass(slots=True)
class CMReportGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class CMReportGateway:
    """Transport layer only: forwards requests to the existing canonical CM
    Report n8n workflows and returns their responses unchanged. No
    business logic, no persistence, no registry, no runtime. Identical
    shape to WorkOrderGateway/MaintenanceHistoryGateway/PumpGateway/
    PMScheduleGateway, per ADR-CM-001's Required Backend Changes.
    """

    def __init__(self, config: CMReportGatewayConfig | None = None):
        self.config = config or CMReportGatewayConfig(
            base_url=os.getenv("AI5R_CM_REPORT_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def create_cm_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", CREATE_PATH, body=payload)

    def get_cm_report(self, cm_report_code: str) -> dict[str, Any]:
        return self._call("GET", DETAIL_PATH, query={"cm_report_code": cm_report_code})

    def list_cm_reports(self) -> dict[str, Any]:
        return self._call("GET", LIST_PATH)

    def update_cm_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("PUT", UPDATE_PATH, body=payload)

    def delete_cm_report(self, cm_report_code: str) -> dict[str, Any]:
        return self._call("DELETE", DELETE_PATH, query={"cm_report_code": cm_report_code})

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
