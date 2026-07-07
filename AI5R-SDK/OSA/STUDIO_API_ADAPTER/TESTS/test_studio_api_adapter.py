import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.STUDIO_API_ADAPTER import StudioAPIAdapter
from OSA.STUDIO_LIVE_OPS import StudioLiveOps


def test_studio_api_adapter_serializes_snapshot():
    snapshot = StudioLiveOps().build_snapshot(
        goals=[
            {
                "goal_id": "GOAL-001",
                "status": "ACTIVE",
            }
        ],
        runtimes=[
            {
                "runtime_id": "ORG-RUN-GOAL-001",
                "status": "ACTIVE",
            }
        ],
    )

    payload = StudioAPIAdapter().serialize_snapshot(snapshot)

    assert payload["type"] == "AI5R_STUDIO_LIVE_OPS_SNAPSHOT"
    assert payload["version"] == "1.0"
    assert payload["data"]["status"] == "LIVE"
    assert payload["data"]["goals"][0]["goal_id"] == "GOAL-001"
    assert payload["data"]["runtimes"][0]["runtime_id"] == "ORG-RUN-GOAL-001"


def test_studio_api_adapter_serializes_many_snapshots():
    snapshot_a = StudioLiveOps().build_snapshot(
        goals=[
            {
                "goal_id": "GOAL-001",
                "status": "ACTIVE",
            }
        ]
    )
    snapshot_b = StudioLiveOps().build_snapshot(
        goals=[
            {
                "goal_id": "GOAL-002",
                "status": "COMPLETED",
            }
        ]
    )

    payload = StudioAPIAdapter().serialize_many(
        [
            snapshot_a,
            snapshot_b,
        ]
    )

    assert payload["type"] == "AI5R_STUDIO_LIVE_OPS_SNAPSHOT_LIST"
    assert payload["count"] == 2
    assert payload["data"][0]["goals"][0]["goal_id"] == "GOAL-001"
    assert payload["data"][1]["goals"][0]["goal_id"] == "GOAL-002"


def test_studio_api_adapter_requires_snapshot():
    try:
        StudioAPIAdapter().serialize_snapshot(None)
    except ValueError as error:
        assert str(error) == "snapshot is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_studio_api_adapter_requires_snapshots():
    try:
        StudioAPIAdapter().serialize_many(None)
    except ValueError as error:
        assert str(error) == "snapshots is required"
    else:
        raise AssertionError("ValueError was not raised")
