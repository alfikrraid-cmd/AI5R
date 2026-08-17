from __future__ import annotations

import sys
from pathlib import Path

INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(INGESTION_PATH))

from ltsa_internal_component_upsert import plan_internal_component_import  # noqa: E402


def test_plan_internal_component_import_upgrades_pending_component_without_duplicate():
    projection = {
        "internal_component_master": [
            {
                "component_id": "LTSA-IC-NEW",
                "component_class": "O_RING",
                "gpn_number": "81060235",
                "gpn_status": "GPN_ASSIGNED",
                "identity_fingerprint": "O_RING|O-RING FFKM 229|229|",
                "description": "O-RING FFKM 229",
                "size_text": "229",
                "specification": None,
                "source_workbook_name": "wb",
                "source_sheet_name": "O-Ring",
                "source_row_number": 11,
                "remarks": None,
            }
        ],
        "internal_component_stock": [],
        "seal_internal_component_link": [],
    }
    state = {
        "internal_components": [
            {
                "component_id": "LTSA-IC-PENDING",
                "component_class": "O_RING",
                "gpn_number": None,
                "gpn_status": "GPN_PENDING",
                "identity_fingerprint": "O_RING|O-RING FFKM 229|229|",
                "description": "O-RING FFKM 229",
            }
        ],
        "internal_component_stock": [],
        "seal_internal_component_link": [],
    }
    plan, conflicts, resolved = plan_internal_component_import(
        projection,
        state,
        normalize_text=lambda v: None if v is None else str(v),
        is_blank=lambda v: v is None or (isinstance(v, str) and not v.strip()),
    )

    assert conflicts == []
    assert resolved == {"LTSA-IC-NEW": "LTSA-IC-PENDING"}
    assert plan["internal_components"]["insert"] == []
    assert plan["internal_components"]["update"][0]["component_id"] == "LTSA-IC-PENDING"
    assert plan["internal_components"]["update"][0]["fields"] == {
        "gpn_number": "81060235",
        "gpn_status": "GPN_ASSIGNED",
        "size_text": "229",
        "source_workbook_name": "wb",
        "source_sheet_name": "O-Ring",
        "source_row_number": 11,
    }


def test_plan_internal_component_import_rejects_conflicting_gpn_assignment():
    projection = {
        "internal_component_master": [
            {
                "component_id": "LTSA-IC-PROJ",
                "component_class": "O_RING",
                "gpn_number": "81060235",
                "gpn_status": "GPN_ASSIGNED",
                "identity_fingerprint": "O_RING|O-RING OTHER|229|",
                "description": "O-RING OTHER",
                "size_text": "229",
                "specification": None,
                "source_workbook_name": "wb",
                "source_sheet_name": "O-Ring",
                "source_row_number": 12,
                "remarks": None,
            }
        ],
        "internal_component_stock": [],
        "seal_internal_component_link": [],
    }
    state = {
        "internal_components": [
            {
                "component_id": "LTSA-IC-GPN",
                "component_class": "O_RING",
                "gpn_number": "81060235",
                "gpn_status": "GPN_ASSIGNED",
                "identity_fingerprint": "O_RING|O-RING FFKM 229|229|",
                "description": "O-RING FFKM 229",
            },
            {
                "component_id": "LTSA-IC-PENDING",
                "component_class": "O_RING",
                "gpn_number": None,
                "gpn_status": "GPN_PENDING",
                "identity_fingerprint": "O_RING|O-RING OTHER|229|",
                "description": "O-RING OTHER",
            },
        ],
        "internal_component_stock": [],
        "seal_internal_component_link": [],
    }
    plan, conflicts, _ = plan_internal_component_import(
        projection,
        state,
        normalize_text=lambda v: None if v is None else str(v),
        is_blank=lambda v: v is None or (isinstance(v, str) and not v.strip()),
    )

    assert len(conflicts) == 1
    assert plan["internal_components"]["rejected"] == ["LTSA-IC-PROJ"]
