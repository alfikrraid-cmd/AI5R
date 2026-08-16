from __future__ import annotations

import sys
from pathlib import Path

INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(INGESTION_PATH))

from ltsa_pump_inventory_ingestion import (  # noqa: E402
    build_projection,
    build_seal_code,
    project_grouped_inventory_rows,
    project_out_of_stock_rows,
)


def test_project_grouped_inventory_rows_carries_forward_grouped_cells():
    rows = [
        (8, {1: "NO."}),
        (
            11,
            {
                2: "Basic Seal",
                6: '1.1/4"',
                7: "300-P-1A",
                8: "SC",
                9: "OLD",
                10: "E12926",
                11: "PL II",
                12: "T48MP",
                13: "OH2",
                14: "HSC & SPK",
                15: "1",
            },
        ),
        (
            12,
            {
                7: "300-P-1B",
            },
        ),
    ]

    projected = project_grouped_inventory_rows(rows)

    assert projected == [
        {
            "row_number": 11,
            "tag_number": "300-P-1A",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": "SC",
            "series_status": "OLD",
            "drawing_ref": "E12926",
            "area": "PL II",
            "seal_type": "T48MP",
            "pump_type": "OH2",
            "contract": "HSC & SPK",
            "stock_material": "1",
        },
        {
            "row_number": 12,
            "tag_number": "300-P-1B",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": None,
            "series_status": None,
            "drawing_ref": None,
            "area": "PL II",
            "seal_type": "T48MP",
            "pump_type": "OH2",
            "contract": "HSC & SPK",
            "stock_material": "1",
        },
    ]


def test_project_out_of_stock_rows_extracts_simple_inventory_rows():
    rows = [
        (7, {1: "1", 2: '1.1/4"', 3: "T48MP"}),
        (8, {1: "2", 2: '1.1/4"', 3: "T0317", 8: "101-P-9"}),
    ]

    projected = project_out_of_stock_rows(rows)

    assert projected == [
        {"shaft_size": '1.1/4"', "seal_type": "T48MP", "remarks": None},
        {"shaft_size": '1.1/4"', "seal_type": "T0317", "remarks": "101-P-9"},
    ]


def test_build_projection_reuses_known_seal_codes_and_dedupes_stock():
    mechseal_rows = [
        {
            "row_number": 11,
            "tag_number": "300-P-1A",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": "SC",
            "series_status": "OLD",
            "drawing_ref": "E12926",
            "area": "PL II",
            "seal_type": "T48MP",
            "pump_type": "OH2",
            "contract": "HSC & SPK",
            "stock_material": "1",
        },
        {
            "row_number": 12,
            "tag_number": "300-P-1B",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": "SC",
            "series_status": "OLD",
            "drawing_ref": "E12926",
            "area": "PL II",
            "seal_type": "T48MP",
            "pump_type": "OH2",
            "contract": "HSC & SPK",
            "stock_material": "1",
        },
        {
            "row_number": 16,
            "tag_number": "101-P-9A",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": "SC",
            "series_status": None,
            "drawing_ref": None,
            "area": "CDU",
            "seal_type": "T0317",
            "pump_type": "GEAR OIL PUMP",
            "contract": "HSC & SPK",
            "stock_material": "4 Set",
        },
    ]
    gudang_rows = [
        {
            "row_number": 11,
            "tag_number": "300-P-1A",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": None,
            "series_status": None,
            "drawing_ref": None,
            "area": "PL II",
            "seal_type": "T48MP",
            "pump_type": "OH2",
            "contract": "HSC & SPK",
            "stock_material": "1",
        },
        {
            "row_number": 16,
            "tag_number": "101-P-9A",
            "description": "Basic Seal",
            "shaft_size": '1.1/4"',
            "critical_status": None,
            "series_status": None,
            "drawing_ref": None,
            "area": "CDU",
            "seal_type": "T0317",
            "pump_type": "GEAR OIL PUMP",
            "contract": "HSC & SPK",
            "stock_material": "4 Set",
        },
    ]
    kosong_rows = [{"shaft_size": '1.1/4"', "seal_type": "T0317", "remarks": "101-P-9"}]

    projection = build_projection(
        mechseal_rows,
        gudang_rows,
        kosong_rows,
        known_seals=[{"seal_code": "SC-EXISTING", "seal_name": "T48MP", "shaft_size": '1.1/4"'}],
    )

    assert [row["tag_number"] for row in projection["ltsa_pumps"]] == [
        "101-P-9A",
        "300-P-1A",
        "300-P-1B",
    ]
    assert projection["seal_registry"] == [
        {
            "seal_code": "LTSA-SEAL-T0317-1-1-4",
            "seal_name": "T0317",
            "manufacturer": "John Crane",
            "model": "T0317",
            "shaft_size": '1.1/4"',
            "status": "ACTIVE",
        },
        {
            "seal_code": "SC-EXISTING",
            "seal_name": "T48MP",
            "manufacturer": "John Crane",
            "model": "T48MP",
            "shaft_size": '1.1/4"',
            "status": "ACTIVE",
        },
    ]
    assert projection["seal_stock"] == [
        {
            "seal_code": "LTSA-SEAL-T0317-1-1-4",
            "quantity_on_hand": 0,
            "reorder_point": 1,
            "location": None,
            "lifecycle_status": "OUT_OF_STOCK",
            "notes": "101-P-9",
        },
        {
            "seal_code": "SC-EXISTING",
            "quantity_on_hand": 1,
            "reorder_point": 1,
            "location": "Gudang",
            "lifecycle_status": "IN_STOCK",
            "notes": None,
        },
    ]
    assert projection["seal_pump_compatibility"] == [
        {"seal_code": "LTSA-SEAL-T0317-1-1-4", "pump_tag_number": "101-P-9A", "notes": "HSC & SPK"},
        {"seal_code": "SC-EXISTING", "pump_tag_number": "300-P-1A", "notes": "HSC & SPK"},
        {"seal_code": "SC-EXISTING", "pump_tag_number": "300-P-1B", "notes": "HSC & SPK"},
    ]
    assert projection["metadata"]["pump_count"] == 3
    assert projection["metadata"]["seal_count"] == 2
    assert projection["metadata"]["seal_stock_count"] == 2
    assert projection["metadata"]["compatibility_count"] == 3


def test_build_seal_code_is_deterministic_for_name_and_size():
    assert build_seal_code("T48MP / T909", '1.1/4"') == "LTSA-SEAL-T48MP-T909-1-1-4"


# --- MWO-LTSA-PUMP-SEAL-DATA-WIRING-001 -- Seal Type + Seal Size V1 identity ---
#
# The scenarios above (test_build_projection_reuses_known_seal_codes_and_
# dedupes_stock) already prove "same type + same size -> one compatible
# group" (300-P-1A/300-P-1B both resolve to SC-EXISTING) and "one seal
# requirement -> many pumps" (SC-EXISTING's stock stays quantity_on_hand=1,
# never multiplied, even with two compatible pumps). These new cases close
# the remaining gaps from this MWO's own required test list.


def test_same_type_different_size_produces_two_distinct_seal_groups():
    mechseal_rows = [
        {"row_number": 11, "tag_number": "400-P-1A", "shaft_size": '3-1/2"', "area": "PL III", "seal_type": "T48MP"},
        {"row_number": 12, "tag_number": "400-P-1B", "shaft_size": '2-1/8"', "area": "PL III", "seal_type": "T48MP"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    seal_codes_by_tag = {row["pump_tag_number"]: row["seal_code"] for row in projection["seal_pump_compatibility"]}
    assert seal_codes_by_tag["400-P-1A"] != seal_codes_by_tag["400-P-1B"]
    assert projection["metadata"]["seal_count"] == 2


def test_sister_pumps_with_different_seals_are_never_merged():
    # Real domain rule: A/B/AR/BR sister pumps are distinct physical pumps.
    # Unlike the identical-seal fixture above, these two report genuinely
    # different Existing Seal Type source values -- nothing may infer or
    # copy 211-P-13A's seal onto 211-P-13B.
    mechseal_rows = [
        {"row_number": 11, "tag_number": "211-P-13A", "shaft_size": '2-1/8"', "area": "Amine", "seal_type": "T48MP"},
        {"row_number": 12, "tag_number": "211-P-13B", "shaft_size": '1-3/4"', "area": "Amine", "seal_type": "T3805"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    seals_by_tag = {row["pump_tag_number"]: row["seal_code"] for row in projection["seal_pump_compatibility"]}
    assert seals_by_tag["211-P-13A"] != seals_by_tag["211-P-13B"]
    assert len(projection["seal_pump_compatibility"]) == 2


def test_missing_drawing_ref_does_not_block_pump_or_compatibility():
    mechseal_rows = [
        {"row_number": 11, "tag_number": "500-P-1", "shaft_size": '2"', "area": "Reaktor", "seal_type": "T48MP", "drawing_ref": None}
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["ltsa_pumps"][0]["tag_number"] == "500-P-1"
    assert projection["ltsa_pumps"][0]["drawing_ref"] is None
    assert len(projection["seal_pump_compatibility"]) == 1


def test_missing_seal_size_does_not_fabricate_a_compatibility_relationship():
    mechseal_rows = [
        {"row_number": 11, "tag_number": "600-P-1", "shaft_size": None, "area": "Fraksinasi", "seal_type": "T48MP"}
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["ltsa_pumps"][0]["tag_number"] == "600-P-1"  # pump itself still imported
    assert projection["seal_registry"] == []
    assert projection["seal_pump_compatibility"] == []  # no fabricated seal identity/relationship


# --- MWO-LTSA-SEAL-SIZE-PLACEHOLDER-FIX-001 -- "-" Seal Size placeholder ---
#
# Real workbook defect (MWO-LTSA-PUMP-SEAL-PRODUCTION-DRYRUN-001): 11 rows
# carry the literal placeholder "-" as Seal Size, previously fabricating a
# shared "UNSPEC" seal identity/compatibility instead of being treated as
# missing, the same way None already was.


def test_dash_seal_size_is_unresolved_like_missing_size():
    mechseal_rows = [
        {"row_number": 271, "tag_number": "212-P-11A", "shaft_size": "-", "area": "PL II", "seal_type": "8AB/8AB/8AB"}
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["ltsa_pumps"][0]["tag_number"] == "212-P-11A"  # pump itself still imported
    assert projection["seal_registry"] == []  # no fabricated "UNSPEC" seal identity
    assert projection["seal_pump_compatibility"] == []  # no fabricated compatibility relationship


def test_dash_seal_size_in_gudang_stock_row_does_not_fabricate_stock():
    mechseal_rows = [
        {"row_number": 271, "tag_number": "212-P-11A", "shaft_size": "-", "area": "PL II", "seal_type": "8AB/8AB/8AB"}
    ]
    gudang_rows = [
        {"row_number": 271, "tag_number": "212-P-11A", "shaft_size": "-", "area": "PL II", "seal_type": "8AB/8AB/8AB", "stock_material": "3"}
    ]

    projection = build_projection(mechseal_rows, gudang_rows, [])

    assert projection["seal_stock"] == []  # no stock record fabricated against an unresolved identity


def test_real_size_alongside_a_dash_size_row_still_resolves_normally():
    # Proves the fix is scoped to the placeholder row only -- a real size
    # elsewhere for a DIFFERENT type is unaffected (no cross-contamination
    # via the shared identities set/dict).
    mechseal_rows = [
        {"row_number": 271, "tag_number": "212-P-11A", "shaft_size": "-", "area": "PL II", "seal_type": "8AB/8AB/8AB"},
        {"row_number": 272, "tag_number": "300-P-1A", "shaft_size": '2"', "area": "PL II", "seal_type": "T48MP"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert len(projection["seal_pump_compatibility"]) == 1
    assert projection["seal_pump_compatibility"][0]["pump_tag_number"] == "300-P-1A"


def test_other_missing_size_placeholder_tokens_are_also_unresolved():
    mechseal_rows = [
        {"row_number": 1, "tag_number": "P-1", "shaft_size": "N/A", "area": "A", "seal_type": "T48MP"},
        {"row_number": 2, "tag_number": "P-2", "shaft_size": "Unknown", "area": "A", "seal_type": "T48MP"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["seal_pump_compatibility"] == []
    assert len(projection["ltsa_pumps"]) == 2  # both pumps still imported


def test_one_pump_multiple_seals_when_source_reports_more_than_one_type():
    mechseal_rows = [
        {"row_number": 11, "tag_number": "700-P-1", "shaft_size": '2"', "area": "Reaktor", "seal_type": "T48MP"},
        {"row_number": 12, "tag_number": "700-P-1", "shaft_size": '2"', "area": "Reaktor", "seal_type": "T3805"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert len(projection["ltsa_pumps"]) == 1  # one physical pump
    assert {row["seal_code"] for row in projection["seal_pump_compatibility"]}.__len__() == 2


def test_duplicate_identical_source_rows_produce_no_duplicate_compatibility_row():
    mechseal_rows = [
        {"row_number": 11, "tag_number": "800-P-1", "shaft_size": '2"', "area": "Reaktor", "seal_type": "T48MP"},
        {"row_number": 12, "tag_number": "800-P-1", "shaft_size": '2"', "area": "Reaktor", "seal_type": "T48MP"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert len(projection["seal_pump_compatibility"]) == 1


# --- MWO-LTSA-SEAL-TYPE-INVALID-GUARD-001 -- invalid/junk Seal Type -------
#
# Real workbook defect: row 142 (tag 946-P-4C) has a literal "`" as its
# Seal Type cell -- a real, valid Seal Size ('2.3/4"') alongside it -- which
# previously survived _normalize_seal_name unchanged and, via
# build_seal_code's own _slug() reduction (no alphanumeric characters left),
# fabricated seal_code LTSA-SEAL-UNSPEC-2-3-4.


def test_backtick_seal_type_does_not_fabricate_an_unspec_identity():
    mechseal_rows = [
        {"row_number": 142, "tag_number": "946-P-4C", "shaft_size": '2.3/4"', "area": "OM 2", "seal_type": "`"}
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["ltsa_pumps"][0]["tag_number"] == "946-P-4C"  # pump itself still imported
    assert projection["seal_registry"] == []
    assert projection["seal_pump_compatibility"] == []
    assert not any(row["seal_code"].startswith("LTSA-SEAL-UNSPEC") for row in projection["seal_registry"])


def test_other_symbol_only_seal_types_also_rejected():
    mechseal_rows = [
        {"row_number": 1, "tag_number": "P-1", "shaft_size": '2"', "area": "A", "seal_type": "***"},
        {"row_number": 2, "tag_number": "P-2", "shaft_size": '2"', "area": "A", "seal_type": "??"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["seal_pump_compatibility"] == []
    assert len(projection["ltsa_pumps"]) == 2  # both pumps still imported


def test_placeholder_seal_type_tokens_rejected_alongside_valid_size():
    mechseal_rows = [
        {"row_number": 1, "tag_number": "P-1", "shaft_size": '2"', "area": "A", "seal_type": "N/A"},
        {"row_number": 2, "tag_number": "P-2", "shaft_size": '2"', "area": "A", "seal_type": "Unknown"},
        {"row_number": 3, "tag_number": "P-3", "shaft_size": '2"', "area": "A", "seal_type": "Belum Diketahui"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert projection["seal_pump_compatibility"] == []
    assert len(projection["ltsa_pumps"]) == 3


def test_valid_seal_type_still_resolves_normally_alongside_the_guard():
    mechseal_rows = [
        {"row_number": 1, "tag_number": "P-1", "shaft_size": '2"', "area": "A", "seal_type": "T48MP"}
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert len(projection["seal_registry"]) == 1
    assert len(projection["seal_pump_compatibility"]) == 1
    assert not projection["seal_registry"][0]["seal_code"].startswith("LTSA-SEAL-UNSPEC")


def test_tandem_seal_55mm_still_resolves_once_and_covers_all_five_pumps():
    mechseal_rows = [
        {"row_number": 260, "tag_number": "945-P-7A", "shaft_size": "55MM", "area": "LPG", "seal_type": "TANDEM SEAL"},
        {"row_number": 261, "tag_number": "945-P-7B", "shaft_size": "55MM", "area": "LPG", "seal_type": "TANDEM SEAL"},
        {"row_number": 262, "tag_number": "945-P-7C", "shaft_size": "55MM", "area": "LPG", "seal_type": "TANDEM SEAL"},
        {"row_number": 263, "tag_number": "140-P-24A", "shaft_size": "55MM", "area": "DCU", "seal_type": "TANDEM SEAL"},
        {"row_number": 264, "tag_number": "140-P-24B", "shaft_size": "55MM", "area": "DCU", "seal_type": "TANDEM SEAL"},
    ]

    projection = build_projection(mechseal_rows, [], [])

    assert len(projection["seal_registry"]) == 1
    tags = {row["pump_tag_number"] for row in projection["seal_pump_compatibility"]}
    assert tags == {"945-P-7A", "945-P-7B", "945-P-7C", "140-P-24A", "140-P-24B"}
