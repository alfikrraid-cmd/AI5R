import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import Department, OrganizationRuntime


def test_organization_runtime_integration():

    runtime = OrganizationRuntime(
        name="AI5R Digital Company",
    )

    runtime.add_department(Department("Marketing"))
    runtime.add_department(Department("Finance"))

    message = runtime.send_message(
        sender="CEO",
        receiver="Marketing",
        content="Prepare campaign strategy",
    )

    delegation = runtime.delegate(
        delegator="CEO",
        delegatee="Marketing Manager",
        task="Create launch campaign",
    )

    meeting = runtime.schedule_meeting(
        title="Launch Planning",
        participants=[
            "CEO",
            "Marketing Manager",
            "Finance Manager",
        ],
        agenda=[
            "Campaign strategy",
            "Budget review",
        ],
    )

    status = runtime.status()

    assert message["status"] == "SENT"
    assert delegation["status"] == "DELEGATED"
    assert meeting["status"] == "SCHEDULED"

    assert status["organization"] == "AI5R Digital Company"
    assert status["departments"] == 2
    assert status["messages"] == 1
    assert status["delegations"] == 1
    assert status["meetings"] == 1
