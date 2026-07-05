import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.ACMS.acms_manifest import ACMSManifest
from ARCHITECTURE.ACMS.manufacturing_line_contract import (
    ManufacturingLineContract,
)


def test_contract_validation():
    contract = ManufacturingLineContract(
        line_code="KML",
        line_name="Knowledge Manufacturing Line",
        input_object="MEMORY_OBJECT",
        output_object="KNOWLEDGE_OBJECT",
        stations=[
            "Extraction Station",
            "Classification Station",
        ],
    )

    assert contract.validate() is True


def test_contract_station_count():
    contract = ManufacturingLineContract(
        line_code="RGL",
        line_name="Reasoning Manufacturing Line",
        input_object="KNOWLEDGE_OBJECT",
        output_object="REASONING_OBJECT",
        stations=[
            "Premise",
            "Evidence",
            "Inference",
        ],
    )

    assert contract.station_count() == 3


def test_manifest_contracts_are_valid():
    contracts = ACMSManifest.contracts()

    assert len(contracts) >= 6

    for contract in contracts:
        assert contract.validate() is True


def test_manifest_contract_codes_match():
    codes = [c.line_code for c in ACMSManifest.contracts()]

    assert "KML" in codes
    assert "RGL" in codes
    assert "DML" in codes
    assert "EML" in codes
    assert "LML" in codes
