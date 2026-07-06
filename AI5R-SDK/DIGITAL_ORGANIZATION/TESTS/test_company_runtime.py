import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import (
    CompanyRuntime,
    Department,
    OrganizationRuntime,
)


def test_company_boot():
    org = OrganizationRuntime("AI5R")

    runtime = CompanyRuntime(org)

    result = runtime.boot()

    assert result["status"] == "RUNNING"
    assert runtime.state == "RUNNING"


def test_company_shutdown():
    org = OrganizationRuntime("AI5R")

    runtime = CompanyRuntime(org)

    runtime.boot()
    result = runtime.shutdown()

    assert result["status"] == "STOPPED"
    assert runtime.state == "STOPPED"


def test_company_health():
    org = OrganizationRuntime("AI5R")

    org.add_department(Department("Engineering"))
    org.add_department(Department("Finance"))

    org.send_message(
        sender="CEO",
        receiver="Engineering",
        content="Build AI5R OS",
    )

    org.delegate(
        delegator="CEO",
        delegatee="CTO",
        task="Lead development",
    )

    org.schedule_meeting(
        title="Sprint Planning",
        participants=["CEO", "CTO"],
        agenda=["Roadmap"],
    )

    runtime = CompanyRuntime(org)

    runtime.boot()

    health = runtime.health()

    assert health["organization"] == "AI5R"
    assert health["state"] == "RUNNING"
    assert health["departments"] == 2
    assert health["messages"] == 1
    assert health["delegations"] == 1
    assert health["meetings"] == 1
