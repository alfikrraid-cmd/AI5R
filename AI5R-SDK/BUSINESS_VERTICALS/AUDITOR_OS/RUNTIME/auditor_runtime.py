from dataclasses import dataclass
from datetime import UTC, datetime

from BUSINESS_VERTICALS.RUNTIME import BaseVerticalRuntime


@dataclass
class AuditorVertical:
    vertical_id: str
    name: str
    domain: str
    agents: list[str]
    created_at: str = datetime.now(UTC).isoformat()


class AuditorRuntime(BaseVerticalRuntime):
    PRODUCT_NAME = "Auditor OS"

    def __init__(self, root_path="."):
        super().__init__(root_path=root_path)
        self.verticals = {}

    def register(self, vertical: AuditorVertical):
        self.verticals[vertical.vertical_id] = vertical
        return {
            "status": "REGISTERED",
            "vertical_id": vertical.vertical_id,
        }

    def get(self, vertical_id: str):
        return self.verticals.get(vertical_id)
