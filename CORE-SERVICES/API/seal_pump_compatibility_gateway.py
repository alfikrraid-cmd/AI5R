from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

LIST_PATH = "ltsa/seal-pump-compatibility/list"


@dataclass(slots=True)
class SealPumpCompatibilityGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class SealPumpCompatibilityGateway:
    """Transport layer only: forwards requests to the existing canonical
    Seal-Pump Compatibility n8n workflow (BUILD-PACKS/BP-SEAL-PUMP-
    COMPATIBILITY, MWO-LTSA-030) and returns its response unchanged. No
    business logic, no persistence, no registry, no runtime. List only --
    the only method Inventory Context (MWO-INV-CTX-001) needs to resolve
    which seals are compatible with a given pump (composition filters the
    list by pump_tag_number, the same "filter first" approach
    get_pump_history already uses for maintenance_history); the existing
    create/detail/update/delete n8n workflows are left unexposed here
    until a real Inventory Module MWO requests them.
    """

    def __init__(self, config: SealPumpCompatibilityGatewayConfig | None = None):
        self.config = config or SealPumpCompatibilityGatewayConfig(
            base_url=os.getenv("AI5R_SEAL_PUMP_COMPATIBILITY_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def list_seal_pump_compatibilities(self) -> dict[str, Any]:
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
