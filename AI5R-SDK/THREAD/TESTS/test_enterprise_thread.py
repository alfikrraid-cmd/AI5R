import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from THREAD.enterprise_thread import EnterpriseThread


def test_enterprise_thread():
    thread = EnterpriseThread(
        organization_id="ORG-001",
        mission_id="MIS-001",
        thread_name="Opportunity Analysis Thread",
        worker_id="WRK-001",
        digital_thread_id="DT-001",
    )

    assert thread.object_type == "ENTERPRISE_THREAD"
    assert thread.current_station == "MISSION"
    assert thread.status == "ACTIVE"

    thread.move_to("REALITY")

    assert thread.current_station == "REALITY"
    assert len(thread.station_history) == 1
    assert thread.station_history[0]["from"] == "MISSION"
    assert thread.station_history[0]["to"] == "REALITY"

    thread.close()

    assert thread.status == "CLOSED"

    print("TF-001 Enterprise Thread Object OK")


if __name__ == "__main__":
    test_enterprise_thread()
