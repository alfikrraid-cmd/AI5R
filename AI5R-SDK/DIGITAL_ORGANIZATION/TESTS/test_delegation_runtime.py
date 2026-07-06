import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import DelegationRuntime


def test_delegation_runtime():

    runtime = DelegationRuntime()

    result = runtime.delegate(
        delegator="CEO",
        delegatee="Marketing Manager",
        task="Create launch campaign",
    )

    delegation = result["delegation"]

    assert result["status"] == "DELEGATED"
    assert delegation.delegator == "CEO"
    assert delegation.delegatee == "Marketing Manager"
    assert delegation.task == "Create launch campaign"
    assert delegation.status == "DELEGATED"
    assert delegation.delegation_id.startswith("DLG-")

    assert runtime.list_all() == [delegation]
    assert runtime.list_by_delegator("CEO") == [delegation]
    assert runtime.list_by_delegatee("Marketing Manager") == [delegation]

    completed = runtime.complete(delegation.delegation_id)

    assert completed["status"] == "COMPLETED"
    assert completed["delegation"].status == "COMPLETED"
