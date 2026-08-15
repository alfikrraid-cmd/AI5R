from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

DETAIL_PATH = "ltsa/installation/detail"
LIST_PATH = "ltsa/installation/list"


@dataclass(slots=True)
class InstallationGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class InstallationGateway:
    """Transport layer only: forwards requests to the canonical Installation
    Report n8n workflows (BUILD-PACKS/BP-INSTALLATION, MWO-LTSA-060) and
    returns their responses unchanged. No business logic, no persistence,
    no registry, no runtime. Identical shape to
    SealEngineeringDocumentGateway/PMScheduleGateway/PumpGateway. List and
    detail only -- create/update/delete were not requested by MWO-LTSA-060
    and are not implemented here.
    """

    def __init__(self, config: InstallationGatewayConfig | None = None):
        self.config = config or InstallationGatewayConfig(
            base_url=os.getenv("AI5R_INSTALLATION_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def list_installations(self) -> dict[str, Any]:
        return self._call("GET", LIST_PATH)

    def get_installation(self, installation_code: str) -> dict[str, Any]:
        return self._call("GET", DETAIL_PATH, query={"installation_code": installation_code})

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
