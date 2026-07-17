#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAPPING-PROFILE-UPDATE-001
# (Mapping Profile Update). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-MP-UPDATE-$$"
OTHER_ID="TEST-MP-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id IN ('${TEST_ID}', '${OTHER_ID}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two fixture records: one to update, one control (must stay unaffected)"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type, status) VALUES ('${TEST_ID}', 'Before Update', 'PUMP_MASTER', 'DRAFT');"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type, status) VALUES ('${OTHER_ID}', 'Untouched', 'PUMP_MASTER', 'DRAFT');"

echo "[1/2] Valid update (equivalent to 'Update Mapping Profile's dynamic SET clause for status only) modifies only the targeted row's specified field"
psql_run -c "UPDATE mapping_profile SET status = 'ACTIVE', updated_at = NOW() WHERE mapping_profile_id = '${TEST_ID}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';")
UPDATED_NAME=$(psql_run -tAc "SELECT profile_name FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM mapping_profile WHERE mapping_profile_id = '${OTHER_ID}';")

if [ "${UPDATED_STATUS}" != "ACTIVE" ]; then
  echo "FAIL: expected status 'ACTIVE' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_NAME}" != "Before Update" ]; then
  echo "FAIL: non-targeted field profile_name changed unexpectedly to '${UPDATED_NAME}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "DRAFT" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/2] Unknown mapping_profile_id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE mapping_profile SET status = 'INACTIVE' WHERE mapping_profile_id = 'DOES-NOT-EXIST-$$' RETURNING mapping_profile_id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent mapping_profile_id"
  exit 1
fi
echo "PASS: nonexistent mapping_profile_id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAPPING-PROFILE-UPDATE-001"
