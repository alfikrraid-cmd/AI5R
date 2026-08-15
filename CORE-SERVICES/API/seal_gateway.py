from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://localhost:5678/webhook"

LIST_PATH = "ltsa/seal/list"


@dataclass(slots=True)
class SealGatewayConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30


class SealGateway:
    """Transport layer only: forwards requests to the existing canonical
    Seal Registry n8n workflow (BUILD-PACKS/BP-SEAL, MWO-LTSA-030) and
    returns its response unchanged. No business logic, no persistence, no
    registry, no runtime. List only -- the only method Inventory Context
    (MWO-INV-CTX-001) needs to resolve a spare part's name; the existing
    create/detail/update/delete n8n workflows are left unexposed here
    until a real Inventory Module MWO requests them.
    """

    def __init__(self, config: SealGatewayConfig | None = None):
        self.config = config or SealGatewayConfig(
            base_url=os.getenv("AI5R_SEAL_GATEWAY_BASE_URL", DEFAULT_BASE_URL),
        )

    def list_seals(self) -> dict[str, Any]:
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
        except urllib.error.URLError as error:
            # Connection-level failure (refused/unreachable/DNS/timeout) --
            # HTTPError is URLError's own subclass and is already handled
            # above; this is the case where n8n was never reached at all,
            # so there is no HTTP response body to decode. An honest
            # success=False/empty-data result, never a raised exception
            # that would otherwise propagate uncaught into a bare 500 --
            # the same "one gateway being unavailable should not crash the
            # whole endpoint" discipline this codebase already applies
            # elsewhere (e.g. maintenance_intelligence_service.py).
            return {"success": False, "data": [], "error": f"{path} unreachable: {error.reason}"}

        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            # Secondary defense only -- the canonical n8n workflow this
            # gateway calls is the primary fix (a Postgres node feeding
            # this webhook's response chain now has alwaysOutputData set,
            # proven against a real n8n 1.115.3 instance to prevent the
            # zero-row-empty-body response this was written against). A
            # malformed/empty response is still reported honestly
            # (success=False, a real error message) rather than silently
            # treated as an empty result -- an empty string is never
            # reinterpreted as "[]" here, since that would hide a real
            # workflow defect instead of surfacing it.
            return {
                "success": False,
                "data": [],
                "error": f"{path} returned a non-JSON response ({len(raw)} bytes): {error}",
            }
