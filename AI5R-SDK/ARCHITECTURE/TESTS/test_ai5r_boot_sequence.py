import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import AI5RBootSequence
from DIGITAL_ORGANIZATION import CompanyRuntime, OrganizationRuntime


def test_ai5r_boot_sequence():
    company = CompanyRuntime(
        OrganizationRuntime("AI5R")
    )

    sequence = AI5RBootSequence(company)

    result = sequence.boot()

    assert result["status"] == "READY"
    assert result["state"] == "READY"
    assert result["organization"] == "AI5R"

    assert result["executed_tasks"] == [
        "register_service_bus",
        "register_company_runtime",
        "boot_company_runtime",
    ]

    assert result["services"] == [
        "company_runtime",
        "service_bus",
    ]

    assert result["events"] == [
        "COMPANY_CONNECTED",
    ]

    assert company.state == "RUNNING"
