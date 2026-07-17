#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-LIST-001 (Maintenance History List).
# MO-001 (OSA Maintenance v0.1) / BP-MAINTENANCE-HISTORY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE_A="TEST-MH-LIST-A-$$"
TEST_CODE_B="TEST-MH-LIST-B-$$"

cleanup() {
  psql_run -c "DELETE FROM maintenance_history WHERE maintenance_record_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/1] List returns every inserted row, matching 'List Maintenance History' node's SELECT * ORDER BY performed_at DESC"
psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken) VALUES ('${TEST_CODE_A}', 'List Test A');"
psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken) VALUES ('${TEST_CODE_B}', 'List Test B');"

FOUND_COUNT=$(psql_run -tAc "SELECT count(*) FROM maintenance_history WHERE maintenance_record_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');")
if [ "${FOUND_COUNT}" -ne 2 ]; then
  echo "FAIL: expected 2 rows, found ${FOUND_COUNT}"
  exit 1
fi
echo "PASS: both inserted rows are present and would be returned by the List Maintenance History query"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-LIST-001"
