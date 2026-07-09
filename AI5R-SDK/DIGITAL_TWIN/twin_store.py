from DIGITAL_TWIN.digital_twin import DigitalTwin


class DigitalTwinStore:
    def __init__(self) -> None:
        self._twins: dict[str, DigitalTwin] = {}

    def register(self, twin: DigitalTwin) -> DigitalTwin:
        self._twins[twin.entity_id] = twin
        return twin

    def get(self, entity_id: str) -> DigitalTwin:
        if entity_id not in self._twins:
            raise KeyError(f"Digital twin not found: {entity_id}")
        return self._twins[entity_id]

    def upsert(
        self,
        entity_id: str,
        entity_type: str,
        status: str = "ACTIVE",
        state: dict | None = None,
        metadata: dict | None = None,
    ) -> DigitalTwin:
        if entity_id in self._twins:
            twin = self._twins[entity_id]
            twin.entity_type = entity_type
            twin.set_status(status)
            twin.update_state(state or {})
            twin.metadata.update(metadata or {})
            return twin

        twin = DigitalTwin(
            entity_id=entity_id,
            entity_type=entity_type,
            status=status,
            state=state or {},
            metadata=metadata or {},
        )
        return self.register(twin)

    def list_all(self) -> list[DigitalTwin]:
        return list(self._twins.values())

    def snapshot(self) -> dict:
        return {
            twin.entity_id: twin.snapshot()
            for twin in self.list_all()
        }
