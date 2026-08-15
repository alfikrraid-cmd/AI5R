from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

CREATE_PATH = "ltsa/condition-monitoring-reading/create"
DETAIL_PATH = "ltsa/condition-monitoring-reading/detail"
LIST_PATH = "ltsa/condition-monitoring-reading/list"


@dataclass(slots=True)
class ConditionMonitoringReadingGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class ConditionMonitoringReadingGateway:
    """Transport layer only: forwards requests to the existing canonical
    Condition Monitoring Reading n8n workflows and returns their
    responses unchanged. No business logic, no persistence, no registry,
    no runtime. Create/detail/list only -- no update/delete -- per
    ADR-CONDITION-MONITORING-001's disclosed judgment call that Readings
    are an append-only measurement log. Deliberately independent of
    CMReportGateway/cm_report -- no shared code, no shared vocabulary.
    """

    def __init__(self, config: ConditionMonitoringReadingGatewayConfig | None = None):
        self.config = config or ConditionMonitoringReadingGatewayConfig(
            base_url=os.getenv(
                "AI5R_CONDITION_MONITORING_READING_GATEWAY_BASE_URL", DEFAULT_BASE_URL
            ),
        )

    def create_condition_monitoring_reading(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", CREATE_PATH, body=payload)

    def get_condition_monitoring_reading(
        self, condition_monitoring_reading_code: str
    ) -> dict[str, Any]:
        return self._call(
            "GET",
            DETAIL_PATH,
            query={"condition_monitoring_reading_code": condition_monitoring_reading_code},
        )

    def list_condition_monitoring_readings(self) -> dict[str, Any]:
        return self._call("GET", LIST_PATH)

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
