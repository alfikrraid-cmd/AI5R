import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.ACMS.acms_manifest import ACMSManifest


def test_acms_manifest_has_system_identity():
    assert ACMSManifest.abbreviation == "ACMS"
    assert "Cognitive Manufacturing" in ACMSManifest.system_name


def test_acms_has_required_manufacturing_lines():
    codes = ACMSManifest.line_codes()

    assert "KML" in codes
    assert "RGL" in codes
    assert "DML" in codes
    assert "EML" in codes
    assert "LML" in codes


def test_reasoning_line_is_defined():
    line = ACMSManifest.find_line("RGL")

    assert line is not None
    assert line.input_object == "KNOWLEDGE_OBJECT"
    assert line.output_object == "REASONING_OBJECT"
    assert "Inference Station" in line.stations
    assert "Conclusion Station" in line.stations


def test_knowledge_line_has_cognitive_stations():
    line = ACMSManifest.find_line("KML")

    assert line is not None
    assert "Knowledge Classification Station" in line.stations
    assert "Knowledge Conflict Station" in line.stations


def test_line_codes_are_unique():
    codes = ACMSManifest.line_codes()

    assert len(codes) == len(set(codes))
