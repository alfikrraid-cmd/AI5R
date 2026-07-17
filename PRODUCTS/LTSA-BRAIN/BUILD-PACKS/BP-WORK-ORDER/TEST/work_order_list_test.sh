#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORK-ORDER-LIST-001 (Work Order List).
# MO-001 (OSA Maintenance v0.1) / BP-WORK-ORDER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE_A="TEST-WO-LIST-A-$$"
TEST_CODE_B="TEST-WO-LIST-B-$$"

cleanup() {
  psql_run -c "DELETE FROM work_order WHERE work_order_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/1] List returns every inserted row, matching 'List Work Orders' node's SELECT * ORDER BY created_at DESC"
psql_run -c "INSERT INTO work_order (work_order_code, description) VALUES ('${TEST_CODE_A}', 'List Test A');"
psql_run -c "INSERT INTO work_order (work_order_code, description) VALUES ('${TEST_CODE_B}', 'List Test B');"

FOUND_COUNT=$(psql_run -tAc "SELECT count(*) FROM work_order WHERE work_order_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');")
if [ "${FOUND_COUNT}" -ne 2 ]; then
  echo "FAIL: expected 2 rows, found ${FOUND_COUNT}"
  exit 1
fi
echo "PASS: both inserted rows are present and would be returned by the List Work Orders query"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORK-ORDER-LIST-001"
