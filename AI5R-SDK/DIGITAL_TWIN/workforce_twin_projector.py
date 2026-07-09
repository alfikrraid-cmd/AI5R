from DIGITAL_TWIN.twin_store import DigitalTwinStore


class WorkforceTwinProjector:
    def __init__(self, twin_store: DigitalTwinStore | None = None) -> None:
        self.twin_store = twin_store or DigitalTwinStore()

    def project(self, event: dict) -> DigitalTwinStore:
        event_type = event.get("event_type")
        payload = event.get("payload", {})

        if event_type == "EMPLOYEE_ACTIVITY_RECORDED":
            self.twin_store.upsert(
                entity_id=payload["employee_id"],
                entity_type="DIGITAL_EMPLOYEE",
                status=payload["status"],
                state={
                    "activity_type": payload["activity_type"],
                    "message": payload["message"],
                    "progress": payload["progress"],
                    "work_item_id": payload.get("work_item_id"),
                    "sprint_id": payload.get("sprint_id"),
                    "mission_id": payload.get("mission_id"),
                    "updated_at": payload.get("updated_at"),
                },
                metadata=payload.get("metadata", {}),
            )

        return self.twin_store

    def project_stream(self, events: list[dict]) -> DigitalTwinStore:
        for event in events:
            self.project(event)
        return self.twin_store
