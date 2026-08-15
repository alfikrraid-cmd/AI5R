from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

LIST_PATH = "ltsa/seal-engineering-document/list"


@dataclass(slots=True)
class SealEngineeringDocumentGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class SealEngineeringDocumentGateway:
    """Transport layer only: forwards requests to the existing canonical
    Seal Engineering Document n8n workflow (BUILD-PACKS/BP-SEAL-
    ENGINEERING-DOCUMENT, MWO-LTSA-030, extended under MWO-LTSA-040B) and
    returns its response unchanged. No business logic, no persistence, no
    registry, no runtime. List only -- the only method Drawing Metadata
    Integration (MWO-LTSA-033) needs to filter to `document_type ==
    'DRAWING'`; the existing create/detail/update/delete n8n workflows are
    left unexposed here until a real Document Module MWO requests them.
    """

    def __init__(self, config: SealEngineeringDocumentGatewayConfig | None = None):
        self.config = config or SealEngineeringDocumentGatewayConfig(
            base_url=os.getenv("AI5R_SEAL_ENGINEERING_DOCUMENT_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def list_seal_engineering_documents(self) -> dict[str, Any]:
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
