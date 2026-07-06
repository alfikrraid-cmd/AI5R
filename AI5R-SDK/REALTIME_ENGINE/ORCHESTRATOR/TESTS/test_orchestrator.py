from REALTIME_ENGINE.ORCHESTRATOR import (
    RealtimeOrchestrator,
)


def test_realtime_orchestrator():

    engine = RealtimeOrchestrator()


    result = engine.process(
        {
            "type": "CUSTOMER_MESSAGE",
            "message": "need recommendation"
        }
    )


    assert result["status"] == "COMPLETED"
    assert result["brain"] == "CONNECTED"
    assert result["action"] == "EXECUTED"
