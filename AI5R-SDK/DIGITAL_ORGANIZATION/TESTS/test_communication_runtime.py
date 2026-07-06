import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import CommunicationRuntime


def test_communication_runtime():

    runtime = CommunicationRuntime()

    result = runtime.send(
        sender="CEO",
        receiver="Marketing Manager",
        content="Create campaign strategy",
    )

    message = result["message"]

    assert result["status"] == "SENT"
    assert message.sender == "CEO"
    assert message.receiver == "Marketing Manager"
    assert message.content == "Create campaign strategy"
    assert message.status == "SENT"
    assert message.message_id.startswith("MSG-")

    assert runtime.inbox("Marketing Manager") == [message]
    assert runtime.outbox("CEO") == [message]

    completed = runtime.mark_completed(message.message_id)

    assert completed["status"] == "COMPLETED"
    assert completed["message"].status == "COMPLETED"
