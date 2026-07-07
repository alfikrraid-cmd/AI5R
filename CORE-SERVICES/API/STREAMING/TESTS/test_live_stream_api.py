import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "AI5R-SDK"))
sys.path.insert(0, str(ROOT / "CORE-SERVICES"))

from API.STREAMING import LiveStreamAPI


def test_live_stream_api_publishes_and_reads_latest_events():
    api = LiveStreamAPI()

    api.publish(
        "GOAL_RECEIVED",
        {
            "goal_id": "GOAL-001",
        },
    )

    payload = api.latest()

    assert payload["type"] == "AI5R_STUDIO_EVENT_STREAM"
    assert payload["version"] == "1.0"
    assert payload["count"] == 1
    assert payload["events"][0]["event_type"] == "GOAL_RECEIVED"
    assert payload["events"][0]["payload"]["goal_id"] == "GOAL-001"


def test_live_stream_api_limits_latest_events():
    api = LiveStreamAPI()

    for index in range(5):
        api.publish(
            "EVENT",
            {
                "index": index,
            },
        )

    payload = api.latest(limit=2)

    assert payload["count"] == 2
    assert payload["events"][0]["payload"]["index"] == 3
    assert payload["events"][1]["payload"]["index"] == 4


def test_live_stream_api_formats_sse_events():
    api = LiveStreamAPI()

    api.publish(
        "RUNTIME_COMPLETED",
        {
            "runtime_id": "ORG-RUN-GOAL-001",
        },
    )

    messages = list(api.sse())

    assert len(messages) == 1
    assert messages[0].startswith("event: RUNTIME_COMPLETED\n")
    assert "data: " in messages[0]

    raw_data = messages[0].split("data: ", 1)[1].strip()
    parsed = json.loads(raw_data)

    assert parsed["event_type"] == "RUNTIME_COMPLETED"
    assert parsed["payload"]["runtime_id"] == "ORG-RUN-GOAL-001"
