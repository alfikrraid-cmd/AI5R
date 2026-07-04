import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from THREAD.enterprise_thread import EnterpriseThread
from THREAD.enterprise_thread_registry import EnterpriseThreadRegistry


def test_enterprise_thread_registry():
    registry = EnterpriseThreadRegistry()

    thread = EnterpriseThread(
        organization_id="ORG-001",
        mission_id="MIS-001",
        thread_name="Opportunity Analysis Thread",
        worker_id="WRK-001",
        digital_thread_id="DT-001",
    )

    registered = registry.register(thread)

    assert registered == thread
    assert registry.exists(thread.thread_id) is True
    assert registry.get(thread.thread_id) == thread
    assert len(registry.list_all()) == 1

    assert registry.list_by_organization("ORG-001") == [thread]
    assert registry.list_by_mission("MIS-001") == [thread]
    assert registry.list_by_worker("WRK-001") == [thread]
    assert registry.list_by_status("ACTIVE") == [thread]
    assert registry.list_by_station("MISSION") == [thread]

    print("TF-002 Enterprise Thread Registry OK")


if __name__ == "__main__":
    test_enterprise_thread_registry()
