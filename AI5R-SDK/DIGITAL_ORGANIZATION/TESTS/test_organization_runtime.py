import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import Department, DigitalOrganization


def test_organization_runtime():

    organization = DigitalOrganization(
        name="AI5R Digital Company",
    )

    marketing = Department("Marketing")
    finance = Department("Finance")

    organization.add_department(marketing)
    organization.add_department(finance)

    assert organization.name == "AI5R Digital Company"
    assert organization.department_count() == 2
    assert organization.get_department("Marketing") == marketing
    assert organization.get_department("Finance") == finance
    assert organization.get_department("HR") is None

    result = organization.send_message(
        sender="CEO",
        receiver="Marketing",
        content="Prepare campaign strategy",
    )

    message = result["message"]

    assert result["status"] == "SENT"
    assert organization.inbox("Marketing") == [message]
    assert message.content == "Prepare campaign strategy"
