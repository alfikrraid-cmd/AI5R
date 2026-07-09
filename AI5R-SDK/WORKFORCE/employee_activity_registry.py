from WORKFORCE.employee_activity import EmployeeActivity


class EmployeeActivityRegistry:
    def __init__(self) -> None:
        self._activities: dict[str, EmployeeActivity] = {}

    def record(self, activity: EmployeeActivity) -> EmployeeActivity:
        self._activities[activity.activity_id] = activity
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

    def snapshot(self) -> list[dict]:
        return [
            {
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
            for activity in self.list_all()
        ]
