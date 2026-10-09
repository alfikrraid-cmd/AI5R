"""
Script to execute the R3B controlled production backfill into current_seal_installation.
Enforces:
1. Frozen manifest SHA256 verification (d4e7940684c1c315e54f3b0399707b155e1bb9666560c48fd19a85a3cf64c279).
2. Exactly 39 rows.
3. Atomic transaction (BEGIN ... COMMIT).
4. No re-derivation.
"""

import csv
import hashlib
import sys
from pathlib import Path

MANIFEST_PATH = Path("ltsa_current_installation_r3a_dry_run.csv")
EXPECTED_SHA256 = "d4e7940684c1c315e54f3b0399707b155e1bb9666560c48fd19a85a3cf64c279"

def sql_quote(val):
    if val is None or val == "":
        return "NULL"
    # escape single quotes
    clean = str(val).replace("'", "''")
    return f"'{clean}'"

def main():
    # 1. Verify manifest SHA256
    manifest_bytes = MANIFEST_PATH.read_bytes()
    actual_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if actual_hash != EXPECTED_SHA256:
        raise ValueError(f"Manifest SHA256 mismatch: expected {EXPECTED_SHA256}, got {actual_hash}")
    print(f"Manifest SHA256 verified: {actual_hash}")

    # 2. Read rows
    with open(MANIFEST_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 39:
        raise ValueError(f"Expected 39 rows in manifest, got {len(rows)}")

    # 3. Construct SQL transaction
    sql_lines = [
        "-- LTSA R3B Production Backfill: 39 frozen manifest rows",
        "BEGIN;",
        "SELECT count(*) FROM public.current_seal_installation; -- Pre-check count (expect 0)"
    ]

    for idx, r in enumerate(rows, start=1):
        pump_tag = sql_quote(r["pump_tag_number"])
        side = sql_quote(r["equipment_side"])
        seal_type = sql_quote(r["seal_type"])
        seal_size = sql_quote(r["seal_size"])
        drawing_no = sql_quote(r["drawing_no"])
        assembly_gpn = sql_quote(r["assembly_gpn"])
        material_code = sql_quote(r["material_code"])
        source_type = sql_quote(r["source_type"])
        source_ref = sql_quote(r["source_reference"])
        source_date = sql_quote(r["source_date"])
        res_status = sql_quote(r["resolution_status"])
        conf_status = sql_quote(r["confidence_status"])
        # installed_at matches source_date
        installed_at = f"{source_date}::timestamptz" if r["source_date"] else "NULL"

        stmt = (
            f"INSERT INTO public.current_seal_installation ("
            f"pump_tag_number, equipment_side, seal_type, seal_size, drawing_no, "
            f"assembly_gpn, material_code, source_type, source_reference, source_date, "
            f"resolution_status, confidence_status, installed_at"
            f") VALUES ("
            f"{pump_tag}, {side}, {seal_type}, {seal_size}, {drawing_no}, "
            f"{assembly_gpn}, {material_code}, {source_type}, {source_ref}, {source_date}, "
            f"{res_status}, {conf_status}, {installed_at}"
            f");"
        )
        sql_lines.append(f"-- Row {idx}: {r['pump_tag_number']} ({r['equipment_side']}) from {r['source_reference']}")
        sql_lines.append(stmt)

    sql_lines.append("COMMIT;")
    sql_lines.append("SELECT count(*) FROM public.current_seal_installation; -- Post-check count (expect 39)")

    sql_content = "\n".join(sql_lines)
    output_path = Path("scripts/r3b_backfill.sql")
    output_path.write_text(sql_content, encoding="utf-8")
    print(f"Generated {output_path} with {len(rows)} INSERT statements.")

if __name__ == "__main__":
    main()
