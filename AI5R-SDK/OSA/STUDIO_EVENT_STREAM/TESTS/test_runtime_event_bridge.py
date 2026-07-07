from OSA.EVENT_BUS_INTEGRATION import OSAEventBusIntegration, OSAEventType
from OSA.STUDIO_EVENT_STREAM.runtime_event_bridge import RuntimeEventBridge
from OSA.STUDIO_EVENT_STREAM import StudioEventStream


def test_runtime_event_bridge_converts_osa_events_to_studio_events():
    runtime_bus = OSAEventBusIntegration()
    studio_stream = StudioEventStream()
    bridge = RuntimeEventBridge(studio_stream=studio_stream)

    runtime_event = runtime_bus.publish(
        OSAEventType.PIPELINE_COMPLETED,
        source="RuntimePipeline",
        payload={
            "goal_id": "GOAL-001",
            "task_count": 1,
        },
    )

    studio_event = bridge.publish_runtime_event(runtime_event)

    assert studio_event.event_type == "PIPELINE_COMPLETED"
    assert studio_event.payload["source"] == "RuntimePipeline"
    assert studio_event.payload["goal_id"] == "GOAL-001"
    assert studio_stream.size() == 1
