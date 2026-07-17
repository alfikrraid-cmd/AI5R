#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-COLUMN-MAPPING-DELETE-001
# (Column Mapping Delete). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
#
# Uses a record created and destroyed solely within this test (not shared
# with column_mapping_detail_test.sh / _update_test.sh fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_MP_ID="TEST-MP-CM-DELETE-$$"
TEST_ID="TEST-CM-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR COLUMN MAPPING DELETE', 'PUMP_MASTER');"
psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute) VALUES ('${TEST_ID}', '${TEST_MP_ID}', 'TAG NO', 'Pump Tag');"

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal"
psql_run -c "DELETE FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this column_mapping_id would now return 404"

echo "[2/2] Unknown column_mapping_id deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM column_mapping WHERE column_mapping_id = 'DOES-NOT-EXIST-$$' RETURNING column_mapping_id;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent column_mapping_id"
  exit 1
fi
echo "PASS: nonexistent column_mapping_id affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-COLUMN-MAPPING-DELETE-001"
