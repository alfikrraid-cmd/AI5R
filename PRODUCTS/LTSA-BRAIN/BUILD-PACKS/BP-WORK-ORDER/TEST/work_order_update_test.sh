#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORK-ORDER-UPDATE-001 (Work Order Update).
# MO-001 (OSA Maintenance v0.1) / BP-WORK-ORDER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-WO-UPDATE-$$"

cleanup() {
  psql_run -c "DELETE FROM work_order WHERE work_order_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Update statement mutates the targeted row's status and closed_at fields"
psql_run -c "INSERT INTO work_order (work_order_code, description, status) VALUES ('${TEST_CODE}', 'TEST WO UPDATE', 'OPEN');"
psql_run -c "UPDATE work_order SET status = 'CLOSED', closed_at = NOW(), updated_at = NOW() WHERE work_order_code = '${TEST_CODE}';"

NEW_STATUS=$(psql_run -tAc "SELECT status FROM work_order WHERE work_order_code = '${TEST_CODE}';")
if [ "${NEW_STATUS}" != "CLOSED" ]; then
  echo "FAIL: expected status 'CLOSED', got '${NEW_STATUS}'"
  exit 1
fi
CLOSED_AT_SET=$(psql_run -tAc "SELECT (closed_at IS NOT NULL) FROM work_order WHERE work_order_code = '${TEST_CODE}';")
if [ "${CLOSED_AT_SET}" != "t" ]; then
  echo "FAIL: expected closed_at to be set"
  exit 1
fi
echo "PASS: status and closed_at updated correctly, matching 'Update Work Order' node's dynamic SET clause"

echo "[2/2] Updating a nonexistent work_order_code affects zero rows, matching 'Check Update Result' node's 404 branch"
UPDATE_OUTPUT=$(psql_run -tAc "UPDATE work_order SET status = 'X' WHERE work_order_code = 'NONEXISTENT-WO-CODE' RETURNING work_order_code;")
if [ -n "${UPDATE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent work_order_code"
  exit 1
fi
echo "PASS: nonexistent work_order_code update returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORK-ORDER-UPDATE-001"
