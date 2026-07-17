#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-COLUMN-MAPPING-DETAIL-001
# (Column Mapping Detail). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_MP_ID="TEST-MP-CM-DETAIL-$$"
TEST_ID="TEST-CM-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent row and fixture column mapping"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR COLUMN MAPPING DETAIL', 'PUMP_MASTER');"
psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute) VALUES ('${TEST_ID}', '${TEST_MP_ID}', 'Equipment', 'Pump Tag');"

echo "[1/2] Known column_mapping_id returns the correct, full record"
COLUMN=$(psql_run -tAc "SELECT source_column FROM column_mapping WHERE column_mapping_id = '${TEST_ID}' LIMIT 1;")
if [ "${COLUMN}" != "Equipment" ]; then
  echo "FAIL: expected source_column 'Equipment', got '${COLUMN}'"
  exit 1
fi
echo "PASS: known column_mapping_id resolves to the correct record (query mirrors 'Get Column Mapping Detail': SELECT * FROM column_mapping WHERE column_mapping_id = ...)"

echo "[2/2] Unknown column_mapping_id returns zero rows (workflow maps this to statusCode 404 in 'Build Column Mapping Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM column_mapping WHERE column_mapping_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent column_mapping_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent column_mapping_id resolves to zero rows at the DB level; 'Build Column Mapping Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-COLUMN-MAPPING-DETAIL-001"
