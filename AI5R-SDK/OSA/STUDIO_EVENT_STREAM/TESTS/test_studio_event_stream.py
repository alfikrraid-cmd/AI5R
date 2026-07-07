import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.STUDIO_EVENT_STREAM import StudioEventStream


def test_publish_event():
    stream = StudioEventStream()

    event = stream.publish(
        "GOAL_CREATED",
        {
            "goal_id": "GOAL-001",
        },
    )

    assert event.event_type == "GOAL_CREATED"
    assert event.payload["goal_id"] == "GOAL-001"
    assert stream.size() == 1


def test_latest_events():
    stream = StudioEventStream()

    for i in range(5):
        stream.publish(
            "EVENT",
            {
                "index": i,
            },
        )

    latest = stream.latest(2)

    assert len(latest) == 2
    assert latest[0].payload["index"] == 3
    assert latest[1].payload["index"] == 4


def test_clear_stream():
    stream = StudioEventStream()

    stream.publish("A", {})
    stream.publish("B", {})

    assert stream.size() == 2

    stream.clear()

    assert stream.size() == 0


def test_event_type_required():
    stream = StudioEventStream()

    try:
        stream.publish("", {})
    except ValueError as error:
        assert str(error) == "event_type is required"
    else:
        raise AssertionError("ValueError was not raised")
