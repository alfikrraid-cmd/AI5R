import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.employment_contract import EmploymentContract


def test_employment_contract():

    contract = EmploymentContract(
        contract_code="FULL_TIME",
        employment_type="FULL_TIME",
        working_hours_per_month=160,
        managed_by="AI5R",
        private_memory=False,
        private_knowledge=False,
        private_kernel=False,
        sla="STANDARD",
    )

    assert contract.object_type == "EMPLOYMENT_CONTRACT"
    assert contract.status == "ACTIVE"
    assert contract.contract_code == "FULL_TIME"
    assert contract.working_hours_per_month == 160
    assert contract.contract_id.startswith("CONTRACT-")
