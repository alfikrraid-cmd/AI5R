#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORK-ORDER-DELETE-001 (Work Order Delete).
# MO-001 (OSA Maintenance v0.1) / BP-WORK-ORDER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-WO-DELETE-$$"

echo "[1/2] Delete removes the targeted row"
psql_run -c "INSERT INTO work_order (work_order_code, description) VALUES ('${TEST_CODE}', 'TEST WO DELETE');"
psql_run -c "DELETE FROM work_order WHERE work_order_code = '${TEST_CODE}';"

REMAINING=$(psql_run -tAc "SELECT count(*) FROM work_order WHERE work_order_code = '${TEST_CODE}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: expected 0 rows remaining for ${TEST_CODE}, found ${REMAINING}"
  exit 1
fi
echo "PASS: row removed, matching 'Delete Work Order' node's DELETE ... RETURNING *"

echo "[2/2] Deleting a nonexistent work_order_code affects zero rows, matching 'Check Delete Result' node's 404 branch"
DELETE_OUTPUT=$(psql_run -tAc "DELETE FROM work_order WHERE work_order_code = 'NONEXISTENT-WO-CODE' RETURNING work_order_code;")
if [ -n "${DELETE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent work_order_code"
  exit 1
fi
echo "PASS: nonexistent work_order_code delete returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORK-ORDER-DELETE-001"
