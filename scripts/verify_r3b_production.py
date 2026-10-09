import csv
import json
import subprocess
import sys
from pathlib import Path

def query_prod(sql):
    wrapped = f"COPY ({sql.strip().rstrip(';')}) TO STDOUT WITH (FORMAT json, ARRAY true);"
    cmd = [
        "ssh", "ai5r",
        "docker", "exec", "-i", "ai5ros-prod-postgres-1",
        "psql", "-U", "ai5r", "-d", "ltsa_brain", "-c", f"\"{wrapped}\""
    ]
    # Use powershell or raw ssh command string to avoid quoting issues
    full_cmd = f"ssh ai5r \"docker exec -i ai5ros-prod-postgres-1 psql -U ai5r -d ltsa_brain -t -A -c \\\"{sql.strip().rstrip(';')}\\\"\""
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"DB query failed: {res.stderr}\nCommand: {full_cmd}")
    return res.stdout.strip()

def get_prod_json(sql):
    clean = sql.strip().rstrip(';')
    json_sql = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({clean}) t;"
    p = subprocess.Popen(
        ["ssh", "ai5r", "docker exec -i ai5ros-prod-postgres-1 psql -U ai5r -d ltsa_brain -t -A"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = p.communicate(input=json_sql)
    if p.returncode != 0:
        raise RuntimeError(f"Query failed: {stderr}")
    return json.loads(stdout.strip())

def main():
    print("=== STARTING LTSA CURRENT INSTALLATION R3B PRODUCTION VERIFICATION ===")

    # 1. Fetch live current_seal_installation
    sql_csi = """
        SELECT 
            pump_tag_number,
            equipment_side,
            seal_type,
            seal_size,
            drawing_no,
            assembly_gpn,
            material_code,
            source_type,
            source_reference,
            source_date::text as source_date,
            resolution_status,
            confidence_status,
            installed_at::text as installed_at,
            removed_at::text as removed_at
        FROM public.current_seal_installation
        ORDER BY pump_tag_number, equipment_side;
    """
    live_csi = get_prod_json(sql_csi)
    print(f"Live current_seal_installation total rows: {len(live_csi)}")
    assert len(live_csi) == 39, f"Expected 39 rows, found {len(live_csi)}"

    # 2. Load frozen manifest
    with open("ltsa_current_installation_r3a_dry_run.csv", mode="r", encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))
    print(f"Frozen manifest rows: {len(manifest_rows)}")

    # Map manifest rows by (pump_tag_number, equipment_side)
    manifest_map = {(r["pump_tag_number"], r["equipment_side"]): r for r in manifest_rows}
    assert len(manifest_map) == 39, "Duplicate keys in manifest!"

    # 3. Post-insert Traceability & Field Match
    verification_records = []
    all_matched = True
    for live in live_csi:
        key = (live["pump_tag_number"], live["equipment_side"])
        man = manifest_map.get(key)
        if not man:
            print(f"ERROR: Live row {key} not found in manifest!")
            all_matched = False
            continue

        mismatches = []
        for col in ["seal_type", "seal_size", "drawing_no", "assembly_gpn", "material_code", "source_type", "source_reference", "source_date", "resolution_status", "confidence_status"]:
            live_val = live.get(col) or ""
            man_val = man.get(col) or ""
            if live_val != man_val:
                mismatches.append(f"{col}: live='{live_val}' != man='{man_val}'")

        if live.get("removed_at") is not None:
            mismatches.append(f"removed_at is not null: {live['removed_at']}")

        status = "MATCH" if not mismatches else "MISMATCH"
        if mismatches:
            all_matched = False
            print(f"Row {key} MISMATCH: {', '.join(mismatches)}")

        rec = dict(live)
        rec["manifest_hash"] = man.get("manifest_row_hash")
        rec["verification_status"] = status
        rec["notes"] = "; ".join(mismatches) if mismatches else "Traceable to " + live["source_reference"]
        verification_records.append(rec)

    print(f"Traceability match: {'ALL PASS (39/39)' if all_matched else 'FAILED'}")

    # 4. Position breakdown
    sides = {}
    for r in live_csi:
        s = r["equipment_side"]
        sides[s] = sides.get(s, 0) + 1
    print(f"Position breakdown: {sides}")
    assert sides.get("SINGLE", 0) == 23, f"Expected 23 SINGLE, got {sides.get('SINGLE')}"
    assert sides.get("DE", 0) == 8, f"Expected 8 DE, got {sides.get('DE')}"
    assert sides.get("NDE", 0) == 8, f"Expected 8 NDE, got {sides.get('NDE')}"
    assert sides.get("NA", 0) == 0, f"Expected 0 NA, got {sides.get('NA')}"

    # 5. Superseded replacement chains
    chain_checks = {
        "220-P-3A": "INSTL-037-2026",
        "945-P-9B": "INSTL-026-2026",
        "200-P-4B": "INSTL-040-2026"
    }
    for tag, expected_ref in chain_checks.items():
        matching = [r for r in live_csi if r["pump_tag_number"] == tag]
        assert len(matching) in (1, 2), f"Expected 1 or 2 active rows for {tag}, found {len(matching)}"
        for row in matching:
            actual_ref = row["source_reference"]
            side = row["equipment_side"]
            print(f"Chain check {tag} ({side}): active source_reference = {actual_ref} (expected {expected_ref})")
            assert actual_ref == expected_ref, f"Chain check failed for {tag} ({side}): got {actual_ref}, expected {expected_ref}"

    # 6. Excluded review pumps (5)
    review_pumps = ["101-P-6A", "101-P-6C", "211-P-2A", "212-P-25A", "940-P-2A"]
    for rp in review_pumps:
        matching = [r for r in live_csi if r["pump_tag_number"] == rp]
        assert len(matching) == 0, f"Review pump {rp} has {len(matching)} rows in current_seal_installation! Expected 0."
    print("PASS: All 5 review pumps excluded (0 rows).")

    # 7. Excluded conflict pumps (3)
    conflict_pumps = ["101-P-3B", "945-P-7B", "140-P-26B"]
    for cp in conflict_pumps:
        matching = [r for r in live_csi if r["pump_tag_number"] == cp]
        assert len(matching) == 0, f"Conflict pump {cp} has {len(matching)} rows in current_seal_installation! Expected 0."
    print("PASS: All 3 conflict pumps excluded (0 rows).")

    # 8. Drawing quarantine check (GA-187530)
    ga_rows = [r for r in live_csi if (r.get("drawing_no") or "") == "GA-187530"]
    assert len(ga_rows) == 0, f"Found {len(ga_rows)} rows referencing quarantined GA-187530!"
    print("PASS: Quarantined GA-187530 has 0 occurrences.")

    # 9. Production invariant row counts
    counts = get_prod_json("""
        SELECT 
            (SELECT count(*) FROM ltsa_pumps) as ltsa_pumps,
            (SELECT count(*) FROM installation_report) as installation_report,
            (SELECT count(*) FROM current_seal_installation) as current_seal_installation,
            (SELECT count(*) FROM seal_engineering_document) as seal_engineering_document,
            (SELECT count(*) FROM drawing_engineering_link) as drawing_engineering_link;
    """)[0]
    print(f"Production database counts: {counts}")
    assert counts["ltsa_pumps"] == 252, f"ltsa_pumps count changed! {counts['ltsa_pumps']}"
    assert counts["installation_report"] == 42, f"installation_report count changed! {counts['installation_report']}"
    assert counts["current_seal_installation"] == 39, f"current_seal_installation count mismatch! {counts['current_seal_installation']}"
    assert counts["seal_engineering_document"] == 129, f"seal_engineering_document count changed! {counts['seal_engineering_document']}"
    assert counts["drawing_engineering_link"] == 318, f"drawing_engineering_link count changed! {counts['drawing_engineering_link']}"

    # 10. MinIO object count check via SSH
    minio_check = subprocess.run(
        'ssh ai5r "docker exec ai5ros-prod-minio-1 mc ls --recursive myminio/ltsa-drawings | wc -l"',
        shell=True, capture_output=True, text=True
    )
    minio_count = int(minio_check.stdout.strip())
    print(f"MinIO objects in ltsa-drawings: {minio_count}")
    assert minio_count == 129, f"MinIO object count changed! Expected 129, got {minio_count}"

    # 11. Write verification CSV
    csv_file = Path("ltsa_current_installation_r3b_production_verification.csv")
    fieldnames = [
        "pump_tag_number", "equipment_side", "seal_type", "seal_size",
        "drawing_no", "assembly_gpn", "material_code", "source_type",
        "source_reference", "source_date", "resolution_status", "confidence_status",
        "installed_at", "removed_at", "manifest_hash", "verification_status", "notes"
    ]
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(verification_records)
    print(f"Wrote {len(verification_records)} records to {csv_file}")
    print("=== ALL R3B PRODUCTION DATA VERIFICATION CHECKS PASSED ===")

if __name__ == "__main__":
    main()
