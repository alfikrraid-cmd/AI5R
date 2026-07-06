from REALTIME_ENGINE import (
    RealtimeEngine,
    RealtimeEvent,
)


def test_realtime_engine_receive_event():

    engine = RealtimeEngine()

    event = RealtimeEvent(
        event_type="CUSTOMER_REQUEST",
        payload={
            "message": "butuh ide bisnis"
        }
    )

    result = engine.ingest(event)

    assert result["status"] == "RECEIVED"


def test_realtime_engine_observation():

    engine = RealtimeEngine()

    event = RealtimeEvent(
        event_type="MARKET_SIGNAL",
        payload={
            "trend": "AI"
        }
    )

    engine.ingest(event)

    result = engine.observe()

    assert result["total_events"] == 1
