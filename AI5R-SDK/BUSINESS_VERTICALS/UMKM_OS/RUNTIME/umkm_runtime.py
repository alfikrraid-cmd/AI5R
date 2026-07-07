from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_RUNTIME import ProductRuntime


@dataclass
class UMKMRuntimeState:
    product: str
    status: str
    active_agents: int
    created_at: str = datetime.now(UTC).isoformat()


class AI5RUMKMOSRuntime:
    def __init__(self, root_path="."):
        self.root_path = Path(root_path)
        self.state = None
        self.product_runtime = ProductRuntime(self.root_path)

    def start(self, config: dict[str, Any]):
        product_name = config.get("product", "UMKM OS")
        agents = config.get("agents", [])

        self.state = UMKMRuntimeState(
            product=product_name,
            status="ACTIVE",
            active_agents=len(agents),
        )

        self.product_runtime.start(
            ProductSpecification(
                product_name=product_name,
                domains=["Marketing", "Sales", "Operations"],
            )
        )

        return {
            "status": "STARTED",
            "product": self.state.product,
        }

    def run_goal(self, goal: str, employee_id: str = "EMP-001"):
        if not self.state:
            raise ValueError("UMKM runtime is not started")

        return self.product_runtime.run_goal(
            product_name=self.state.product,
            goal=goal,
            employee_id=employee_id,
        )

    def health(self):
        if not self.state:
            return "OFFLINE"

        return self.state.status
