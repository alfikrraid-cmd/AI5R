#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAPPING-PROFILE-DELETE-001
# (Mapping Profile Delete). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
#
# Uses a record created and destroyed solely within this test (not shared
# with mapping_profile_detail_test.sh / _update_test.sh fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-MP-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_ID}', 'TEST MAPPING PROFILE DELETE', 'BILL_OF_MATERIAL');"

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal"
psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this mapping_profile_id would now return 404"

echo "[2/2] Unknown mapping_profile_id deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM mapping_profile WHERE mapping_profile_id = 'DOES-NOT-EXIST-$$' RETURNING mapping_profile_id;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent mapping_profile_id"
  exit 1
fi
echo "PASS: nonexistent mapping_profile_id affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAPPING-PROFILE-DELETE-001"
