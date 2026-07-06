from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class DashboardSnapshot:

    system_status: str
    active_agents: int
    decisions: int
    memories: int
    governance: str
    created_at: str = datetime.now(UTC).isoformat()



class DashboardContract:


    def generate(
        self,
        status: dict[str, Any]
    ):

        return DashboardSnapshot(
            system_status=status.get(
                "system_status",
                "ONLINE"
            ),
            active_agents=status.get(
                "active_agents",
                0
            ),
            decisions=status.get(
                "decisions",
                0
            ),
            memories=status.get(
                "memories",
                0
            ),
            governance=status.get(
                "governance",
                "ACTIVE"
            )
        )
