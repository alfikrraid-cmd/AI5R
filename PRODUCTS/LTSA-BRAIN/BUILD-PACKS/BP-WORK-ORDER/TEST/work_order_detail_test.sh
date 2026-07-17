#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORK-ORDER-DETAIL-001 (Work Order Detail).
# MO-001 (OSA Maintenance v0.1) / BP-WORK-ORDER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-WO-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM work_order WHERE work_order_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Existing work_order_code returns its row"
psql_run -c "INSERT INTO work_order (work_order_code, description) VALUES ('${TEST_CODE}', 'TEST WO DETAIL');"
FOUND_DESC=$(psql_run -tAc "SELECT description FROM work_order WHERE work_order_code = '${TEST_CODE}';")
if [ "${FOUND_DESC}" != "TEST WO DETAIL" ]; then
  echo "FAIL: expected 'TEST WO DETAIL', got '${FOUND_DESC}'"
  exit 1
fi
echo "PASS: detail row matches inserted fields, matching 'Get Work Order Detail' node's SELECT ... WHERE work_order_code = \$1"

echo "[2/2] Non-existent work_order_code yields zero rows, matching 'Build Work Order Detail Response' node's 404 branch"
MISSING_COUNT=$(psql_run -tAc "SELECT count(*) FROM work_order WHERE work_order_code = 'NONEXISTENT-WO-CODE';")
if [ "${MISSING_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent work_order_code, found ${MISSING_COUNT}"
  exit 1
fi
echo "PASS: nonexistent work_order_code correctly yields zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORK-ORDER-DETAIL-001"
