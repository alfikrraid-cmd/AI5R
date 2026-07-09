from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.workforce_event_bus import WorkforceEvent, WorkforceEventBus


class EmployeeActivityRegistry:
    def __init__(self, event_bus: WorkforceEventBus | None = None) -> None:
        self._activities: dict[str, EmployeeActivity] = {}
        self.event_bus = event_bus or WorkforceEventBus()

    def record(self, activity: EmployeeActivity) -> EmployeeActivity:
        self._activities[activity.activity_id] = activity
        self.event_bus.publish(
            WorkforceEvent(
                event_type="EMPLOYEE_ACTIVITY_RECORDED",
                source="WORKFORCE",
                payload=self._activity_payload(activity),
            )
        )
        return activity

    def list_all(self) -> list[EmployeeActivity]:
        return list(self._activities.values())

    def list_by_employee(self, employee_id: str) -> list[EmployeeActivity]:
        return [
            activity
            for activity in self._activities.values()
            if activity.employee_id == employee_id
        ]

    def latest_by_employee(self, employee_id: str) -> EmployeeActivity | None:
        activities = self.list_by_employee(employee_id)

        if not activities:
            return None

        return sorted(
            activities,
            key=lambda activity: activity.updated_at,
        )[-1]

    def _activity_payload(self, activity: EmployeeActivity) -> dict:
        return {
            "activity_id": activity.activity_id,
            "employee_id": activity.employee_id,
            "activity_type": activity.activity_type,
            "status": activity.status,
            "message": activity.message,
            "progress": activity.progress,
            "work_item_id": activity.work_item_id,
            "sprint_id": activity.sprint_id,
            "mission_id": activity.mission_id,
            "updated_at": activity.updated_at,
            "metadata": activity.metadata,
        }

    def snapshot(self) -> list[dict]:
        return [
            self._activity_payload(activity)
            for activity in self.list_all()
        ]
