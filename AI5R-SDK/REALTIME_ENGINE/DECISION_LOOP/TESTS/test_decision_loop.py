from REALTIME_ENGINE.DECISION_LOOP import (
    RealtimeDecisionLoop,
)


def test_realtime_decision_loop():

    engine = RealtimeDecisionLoop()

    result = engine.run(
        {
            "event": "CUSTOMER_REQUEST",
            "message": "need business idea"
        }
    )

    assert result["status"] == "EXECUTED"
    assert result["decision"] == "PROCESS_EVENT"
