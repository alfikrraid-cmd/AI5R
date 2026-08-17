from __future__ import annotations

import sys
from pathlib import Path

INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(INGESTION_PATH))

from ltsa_internal_component_ingestion import build_internal_component_projection  # noqa: E402


def test_build_internal_component_projection_preserves_gpn_pending_and_safe_seal_links():
    rows = [
        {
            "source_sheet_name": "O-Ring",
            "source_row_number": 11,
            "component_class": "O_RING",
            "description": "O-RING FFKM 229",
            "size_text": "229",
            "specification": None,
            "gpn_number": "81060235",
            "quantity_on_hand": 1,
            "warehouse_name": "TAP DMI",
            "rack_name": "E",
            "location_tag": None,
            "remarks": None,
            "seal_type": None,
        },
        {
            "source_sheet_name": "Mechanical Seal Assy",
            "source_row_number": 10,
            "component_class": "MECHANICAL_SEAL_ASSY",
            "description": "MECHANICAL SEAL ASSY",
            "size_text": '1.3/8"',
            "specification": None,
            "gpn_number": None,
            "quantity_on_hand": None,
            "warehouse_name": None,
            "rack_name": None,
            "location_tag": None,
            "remarks": None,
            "seal_type": "T8B1",
        },
    ]
    result = build_internal_component_projection(
        rows,
        {("T8B1", '1.3/8"'): "LTSA-SEAL-T8B1-1-3-8"},
        clean_text=lambda v: None if v is None else str(v),
        normalize_size=lambda v: None if v is None else str(v),
        normalize_gpn=lambda v: None if v is None else str(v),
        normalize_seal_name=lambda v: None if v is None else str(v),
    )

    assert result["internal_component_summary"]["component_count"] == 2
    assert result["internal_component_summary"]["gpn_assigned_count"] == 1
    assert result["internal_component_summary"]["gpn_pending_count"] == 1
    assert result["internal_component_summary"]["seal_link_count"] == 1
    assert result["internal_component_summary"]["gpn_pending_backlog"] == {"MECHANICAL_SEAL_ASSY": 1}
