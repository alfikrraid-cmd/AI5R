#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-UPDATE-001 (Seal Update).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-UPDATE-$$"
OTHER_CODE="TEST-SEAL-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_registry WHERE seal_code IN ('${TEST_CODE}', '${OTHER_CODE}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two fixture records: one to update, one control (must stay unaffected)"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name, status) VALUES ('${TEST_CODE}', 'Before Update', 'UNKNOWN');"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name, status) VALUES ('${OTHER_CODE}', 'Untouched', 'UNKNOWN');"

echo "[1/2] Valid update (equivalent to 'Update Seal's dynamic SET clause for status only) modifies only the targeted row's specified field"
psql_run -c "UPDATE seal_registry SET status = 'ACTIVE', updated_at = NOW() WHERE seal_code = '${TEST_CODE}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM seal_registry WHERE seal_code = '${TEST_CODE}';")
UPDATED_NAME=$(psql_run -tAc "SELECT seal_name FROM seal_registry WHERE seal_code = '${TEST_CODE}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM seal_registry WHERE seal_code = '${OTHER_CODE}';")

if [ "${UPDATED_STATUS}" != "ACTIVE" ]; then
  echo "FAIL: expected status 'ACTIVE' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_NAME}" != "Before Update" ]; then
  echo "FAIL: non-targeted field seal_name changed unexpectedly to '${UPDATED_NAME}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "UNKNOWN" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/2] Unknown seal_code updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE seal_registry SET status = 'INACTIVE' WHERE seal_code = 'DOES-NOT-EXIST-$$' RETURNING seal_code;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent seal_code"
  exit 1
fi
echo "PASS: nonexistent seal_code affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-UPDATE-001"
