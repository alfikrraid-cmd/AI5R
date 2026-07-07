from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_RUNTIME import ProductRuntime


@dataclass
class BusinessVertical:
    vertical_id: str
    name: str
    domain: str
    agents: list[str]
    capabilities: list[str]
    created_at: str = datetime.now(UTC).isoformat()


class BaseVerticalRuntime:
    PRODUCT_NAME = "UNKNOWN"

    def __init__(self, root_path="."):
        self.root_path = Path(root_path)
        self.product_runtime = ProductRuntime(self.root_path)
        self.started = False

    def start(self):
        self.product_runtime.start(
            ProductSpecification(
                product_name=self.PRODUCT_NAME,
                domains=[],
            )
        )
        self.started = True

    def run_goal(self, goal: str, employee_id: str = "EMP-001"):
        if not self.started:
            raise ValueError("runtime is not started")

        return self.product_runtime.run_goal(
            product_name=self.PRODUCT_NAME,
            goal=goal,
            employee_id=employee_id,
        )

    def health(self):
        return "ACTIVE" if self.started else "OFFLINE"


class VerticalRuntime:
    def __init__(self):
        self.verticals = {}

    def register(self, vertical: BusinessVertical):
        self.verticals[vertical.vertical_id] = vertical
        return {
            "status": "REGISTERED",
            "vertical_id": vertical.vertical_id,
        }

    def get(self, vertical_id: str):
        return self.verticals.get(vertical_id)

    def list_all(self):
        return list(self.verticals.values())
