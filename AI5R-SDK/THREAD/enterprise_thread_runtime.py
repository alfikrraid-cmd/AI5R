from typing import Any, Dict

from .enterprise_thread import EnterpriseThread
from .enterprise_thread_registry import EnterpriseThreadRegistry


class EnterpriseThreadRuntime:
    """
    Enterprise Thread Runtime

    Objective:
    Provide a single orchestration point for creating, registering,
    moving, closing, and querying Enterprise Cognitive Threads.
    """

    CANONICAL_STATIONS = [
        "MISSION",
        "INTENT",
        "ATTENTION",
        "FOCUS",
        "REALITY",
        "OBSERVATION",
        "UNDERSTANDING",
        "HYPOTHESIS",
        "DECISION",
        "PLANNING",
        "EXECUTION",
        "OUTCOME",
        "LEARNING",
        "WAREHOUSE",
        "EXPERIENCE",
        "MEMORY",
        "KNOWLEDGE",
        "CAPABILITY",
        "COMPETENCY",
        "INNOVATION",
    ]

    def __init__(self, registry=None):
        self.registry = registry or EnterpriseThreadRegistry()

    def create_thread(
        self,
        organization_id: str,
        mission_id: str,
        thread_name: str,
        worker_id: str | None = None,
        digital_thread_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        thread = EnterpriseThread(
            organization_id=organization_id,
            mission_id=mission_id,
            thread_name=thread_name,
            worker_id=worker_id,
            digital_thread_id=digital_thread_id,
            metadata=metadata or {},
        )

        self.registry.register(thread)

        return {
            "status": "CREATED",
            "thread": thread,
        }

    def move_thread(
        self,
        thread_id: str,
        station: str,
    ) -> Dict[str, Any]:
        thread = self.registry.get(thread_id)

        if thread is None:
            return {
                "status": "FAILED",
                "reason": "Thread not found",
                "thread_id": thread_id,
            }

        if station not in self.CANONICAL_STATIONS:
            return {
                "status": "FAILED",
                "reason": "Invalid station",
                "thread_id": thread_id,
                "station": station,
            }

        thread.move_to(station)

        return {
            "status": "MOVED",
            "thread": thread,
        }

    def close_thread(self, thread_id: str) -> Dict[str, Any]:
        thread = self.registry.get(thread_id)

        if thread is None:
            return {
                "status": "FAILED",
                "reason": "Thread not found",
                "thread_id": thread_id,
            }

        thread.close()

        return {
            "status": "CLOSED",
            "thread": thread,
        }

    def get(self, thread_id):
        return self.registry.get(thread_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_organization(self, organization_id):
        return self.registry.list_by_organization(organization_id)

    def list_by_mission(self, mission_id):
        return self.registry.list_by_mission(mission_id)

    def list_by_worker(self, worker_id):
        return self.registry.list_by_worker(worker_id)

    def list_by_status(self, status):
        return self.registry.list_by_status(status)

    def list_by_station(self, station):
        return self.registry.list_by_station(station)
