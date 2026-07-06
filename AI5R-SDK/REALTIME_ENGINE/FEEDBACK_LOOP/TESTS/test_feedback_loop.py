from REALTIME_ENGINE.FEEDBACK_LOOP import (
    CognitiveFeedbackLoop,
)


def test_feedback_learning():

    loop = CognitiveFeedbackLoop()

    loop.record(
        "SEND_RESPONSE",
        {
            "customer": "happy"
        }
    )

    result = loop.learn()

    assert result["status"] == "LEARNING"
    assert result["samples"] == 1
