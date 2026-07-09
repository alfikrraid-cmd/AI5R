from DIGITAL_TWIN.digital_twin import DigitalTwin
from DIGITAL_TWIN.twin_store import DigitalTwinStore


def test_digital_twin_snapshot():
    twin = DigitalTwin(
        entity_id="EMP-001",
        entity_type="DIGITAL_EMPLOYEE",
        status="THINKING",
        state={"progress": 35},
    )

    snapshot = twin.snapshot()

    assert snapshot["twin_id"].startswith("TWIN-")
    assert snapshot["entity_id"] == "EMP-001"
    assert snapshot["entity_type"] == "DIGITAL_EMPLOYEE"
    assert snapshot["status"] == "THINKING"
    assert snapshot["state"]["progress"] == 35


def test_digital_twin_state_update():
    twin = DigitalTwin(
        entity_id="MISSION-001",
        entity_type="MISSION",
    )

    twin.update_state({"progress": 50})
    twin.set_status("RUNNING")

    assert twin.state["progress"] == 50
    assert twin.status == "RUNNING"


def test_twin_store_upserts_new_twin():
    store = DigitalTwinStore()

    twin = store.upsert(
        entity_id="MISSION-001",
        entity_type="MISSION",
        status="RUNNING",
        state={"objective": "Build Login API"},
    )

    assert store.get("MISSION-001") == twin
    assert store.snapshot()["MISSION-001"]["status"] == "RUNNING"


def test_twin_store_updates_existing_twin_without_duplicate():
    store = DigitalTwinStore()

    store.upsert(
        entity_id="EMP-001",
        entity_type="DIGITAL_EMPLOYEE",
        status="THINKING",
        state={"progress": 35},
    )

    store.upsert(
        entity_id="EMP-001",
        entity_type="DIGITAL_EMPLOYEE",
        status="EXECUTING",
        state={"progress": 70},
    )

    assert len(store.list_all()) == 1

    twin = store.get("EMP-001")

    assert twin.status == "EXECUTING"
    assert twin.state["progress"] == 70
