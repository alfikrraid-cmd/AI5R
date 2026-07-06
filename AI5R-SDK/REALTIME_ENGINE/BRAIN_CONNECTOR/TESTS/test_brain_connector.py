from REALTIME_ENGINE.BRAIN_CONNECTOR import (
    RealtimeBrainConnector,
)


def test_brain_connector():

    connector = RealtimeBrainConnector()

    result = connector.send_to_brain(
        {
            "observation": "customer wants business idea"
        }
    )

    assert result["status"] == "CONNECTED"
    assert connector.get_context_count() == 1
