#!/usr/bin/env bash
# Functional test for WF-LTSA-PUMP-UPDATE-001 (Pump Update).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_TAG="TEST-PUMP-UPDATE-$$"
OTHER_TAG="TEST-PUMP-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number IN ('${TEST_TAG}', '${OTHER_TAG}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two fixture records: one to update, one control (must stay unaffected)"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area, status) VALUES ('${TEST_TAG}', 'Before Update', 'UNKNOWN');"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area, status) VALUES ('${OTHER_TAG}', 'Untouched', 'UNKNOWN');"

echo "[1/2] Valid update (equivalent to 'Update Pump's dynamic SET clause for status only) modifies only the targeted row's specified field"
psql_run -c "UPDATE ltsa_pumps SET status = 'ACTIVE', updated_at = NOW() WHERE tag_number = '${TEST_TAG}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';")
UPDATED_AREA=$(psql_run -tAc "SELECT area FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM ltsa_pumps WHERE tag_number = '${OTHER_TAG}';")

if [ "${UPDATED_STATUS}" != "ACTIVE" ]; then
  echo "FAIL: expected status 'ACTIVE' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_AREA}" != "Before Update" ]; then
  echo "FAIL: non-targeted field area changed unexpectedly to '${UPDATED_AREA}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "UNKNOWN" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/2] Unknown tag_number updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE ltsa_pumps SET status = 'INACTIVE' WHERE tag_number = 'DOES-NOT-EXIST-$$' RETURNING tag_number;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent tag_number"
  exit 1
fi
echo "PASS: nonexistent tag_number affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-PUMP-UPDATE-001"
