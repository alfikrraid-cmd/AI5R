from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

CREATE_PATH = "ltsa/pm-occurrence/create"
DETAIL_PATH = "ltsa/pm-occurrence/detail"
LIST_PATH = "ltsa/pm-occurrence/list"


@dataclass(slots=True)
class PMOccurrenceGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class PMOccurrenceGateway:
    """Transport layer only: forwards requests to the existing canonical
    PM Occurrence n8n workflows and returns their responses unchanged. No
    business logic, no persistence, no registry, no runtime. Create/
    detail/list only -- no update/delete -- per ADR-PM-OCCURRENCE-001's
    independently re-evaluated judgment call that Occurrences are an
    append-only completion log, the same conclusion
    ConditionMonitoringReadingGateway reached from the same shape of
    evidence. Deliberately independent of CMReportGateway/cm_report and
    ConditionMonitoringReadingGateway/condition_monitoring_reading -- no
    shared code, no shared vocabulary.
    """

    def __init__(self, config: PMOccurrenceGatewayConfig | None = None):
        self.config = config or PMOccurrenceGatewayConfig(
            base_url=os.getenv("AI5R_PM_OCCURRENCE_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def create_pm_occurrence(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", CREATE_PATH, body=payload)

    def get_pm_occurrence(self, pm_occurrence_code: str) -> dict[str, Any]:
        return self._call("GET", DETAIL_PATH, query={"pm_occurrence_code": pm_occurrence_code})

    def list_pm_occurrences(self) -> dict[str, Any]:
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
