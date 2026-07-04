import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from THREAD.enterprise_thread_runtime import EnterpriseThreadRuntime


def test_enterprise_thread_runtime():
    runtime = EnterpriseThreadRuntime()

    created = runtime.create_thread(
        organization_id="ORG-001",
        mission_id="MIS-001",
        thread_name="Opportunity Analysis Thread",
        worker_id="WRK-001",
        digital_thread_id="DT-001",
        metadata={"source": "unit-test"},
    )

    assert created["status"] == "CREATED"

    thread = created["thread"]

    assert thread.current_station == "MISSION"
    assert runtime.get(thread.thread_id) == thread

    moved = runtime.move_thread(
        thread_id=thread.thread_id,
        station="REALITY",
    )

    assert moved["status"] == "MOVED"
    assert thread.current_station == "REALITY"
    assert len(thread.station_history) == 1

    invalid = runtime.move_thread(
        thread_id=thread.thread_id,
        station="UNKNOWN_STATION",
    )

    assert invalid["status"] == "FAILED"
    assert invalid["reason"] == "Invalid station"

    closed = runtime.close_thread(thread.thread_id)

    assert closed["status"] == "CLOSED"
    assert thread.status == "CLOSED"

    assert runtime.list_by_organization("ORG-001") == [thread]
    assert runtime.list_by_mission("MIS-001") == [thread]
    assert runtime.list_by_worker("WRK-001") == [thread]
    assert runtime.list_by_status("CLOSED") == [thread]
    assert runtime.list_by_station("REALITY") == [thread]

    print("TF-003 Enterprise Thread Runtime OK")


if __name__ == "__main__":
    test_enterprise_thread_runtime()
