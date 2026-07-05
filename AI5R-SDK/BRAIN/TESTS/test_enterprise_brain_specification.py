import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_brain_specification import EnterpriseBrainSpecification


def test_enterprise_brain_specification_defaults():
    spec = EnterpriseBrainSpecification()

    assert spec.specification_id == "EB-SPEC-001"
    assert spec.version == "1.0"
    assert spec.status == "foundation_frozen"
    assert spec.canonical_thread[0] == "reality"
    assert spec.canonical_thread[-1] == "learning"
    assert spec.contracts["input_contract"] == "Reality Object"
    assert spec.contracts["output_contract"] == "Learning Object"


def test_enterprise_brain_specification_to_dict():
    spec = EnterpriseBrainSpecification()
    data = spec.to_dict()

    assert data["name"] == "Enterprise Brain Specification"
    assert data["status"] == "foundation_frozen"
    assert "Everything is an Enterprise Object" in data["principles"]
    assert data["contracts"]["runtime_contract"] == "EnterpriseBrainRuntime"
