from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class APIRequest:
    endpoint: str
    payload: dict


@dataclass
class APIResponse:
    status: str
    data: Any


class APIGateway:
    def __init__(self):
        self.routes: dict[str, Callable[[dict], Any]] = {}
        self.logs: list[APIRequest] = []

    def register(self, endpoint: str, handler: Callable[[dict], Any]):
        self.routes[endpoint] = handler

    def call(self, endpoint: str, payload: dict) -> APIResponse:
        self.logs.append(APIRequest(endpoint, payload))

        if endpoint not in self.routes:
            return APIResponse(status="404", data="NOT_FOUND")

        try:
            result = self.routes[endpoint](payload)
            return APIResponse(status="200", data=result)
        except Exception as e:
            return APIResponse(status="500", data=str(e))

    def snapshot(self):
        return {
            "routes": list(self.routes.keys()),
            "requests": len(self.logs),
        }
