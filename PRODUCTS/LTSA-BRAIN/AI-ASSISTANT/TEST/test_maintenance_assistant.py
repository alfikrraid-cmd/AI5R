"""Behavioral test for the Basic AI Assistant (MO-001 / BP-AI-ASSISTANT).

Unlike the n8n/PostgreSQL-backed registries in this order, this module has
no external dependency -- BRAIN's cognitive pipeline is pure Python -- so
this test can be, and is, actually executed, not merely structurally
validated. Run with: python -m pytest PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/TEST/
or python PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/TEST/test_maintenance_assistant.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintenance_assistant import build_reality, get_maintenance_recommendation  # noqa: E402


def test_build_reality_shape():
    reality = build_reality("P-101", "Vibration 11.2, bearing temperature 92", vibration=11.2, temperature=92)
    assert reality["object_type"] == "reality"
    assert reality["measurements"]["vibration"] == 11.2
    assert reality["measurements"]["temperature"] == 92


def test_high_vibration_and_temperature_yields_a_recommendation():
    result = get_maintenance_recommendation(
        asset_code="P-101",
        findings_text="Vibration 11.2 mm/s, bearing temperature 92 C",
        vibration=11.2,
        temperature=92,
    )
    assert result["asset_code"] == "P-101"
    assert isinstance(result["recommendation"], str) and len(result["recommendation"]) > 0
    assert isinstance(result["confidence_delta"], float)
    assert "selected_hypothesis" in result


def test_low_readings_still_produce_a_general_recommendation():
    result = get_maintenance_recommendation(
        asset_code="P-999",
        findings_text="Routine check, nothing notable",
        vibration=2,
        temperature=40,
    )
    assert result["asset_code"] == "P-999"
    assert isinstance(result["recommendation"], str) and len(result["recommendation"]) > 0


if __name__ == "__main__":
    test_build_reality_shape()
    print("PASS: test_build_reality_shape")
    test_high_vibration_and_temperature_yields_a_recommendation()
    print("PASS: test_high_vibration_and_temperature_yields_a_recommendation")
    test_low_readings_still_produce_a_general_recommendation()
    print("PASS: test_low_readings_still_produce_a_general_recommendation")
    print("ALL TESTS COMPLETE for maintenance_assistant.py")
