import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.enterprise_event import EnterpriseEvent


def test_enterprise_event():
    event = EnterpriseEvent(
        event_type="MissionCreated",
        source="EnterpriseKernel",
        target="MissionControl",
        mission_id="MISSION-001",
        payload={
            "objective": "Build Enterprise Event Contract",
            "priority": "high",
        },
        metadata={
            "module": "EL-004",
            "layer": "Enterprise",
        },
    )

    data = event.to_dict()

    assert data["event_type"] == "MissionCreated"
    assert data["source"] == "EnterpriseKernel"
    assert data["target"] == "MissionControl"
    assert data["mission_id"] == "MISSION-001"
    assert data["payload"]["priority"] == "high"
    assert data["metadata"]["module"] == "EL-004"
    assert data["event_id"] is not None
    assert data["timestamp"] is not None

    print("EL-004 Enterprise Event Contract OK")


if __name__ == "__main__":
    test_enterprise_event()
