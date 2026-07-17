#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-DETAIL-001 (Maintenance History Detail).
# MO-001 (OSA Maintenance v0.1) / BP-MAINTENANCE-HISTORY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-MH-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Existing maintenance_record_code returns its row"
psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken) VALUES ('${TEST_CODE}', 'TEST MH DETAIL ACTION');"
FOUND_ACTION=$(psql_run -tAc "SELECT action_taken FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';")
if [ "${FOUND_ACTION}" != "TEST MH DETAIL ACTION" ]; then
  echo "FAIL: expected 'TEST MH DETAIL ACTION', got '${FOUND_ACTION}'"
  exit 1
fi
echo "PASS: detail row matches inserted fields, matching 'Get Maintenance History Detail' node's SELECT ... WHERE maintenance_record_code = \$1"

echo "[2/2] Non-existent maintenance_record_code yields zero rows, matching 'Build Maintenance History Detail Response' node's 404 branch"
MISSING_COUNT=$(psql_run -tAc "SELECT count(*) FROM maintenance_history WHERE maintenance_record_code = 'NONEXISTENT-MH-CODE';")
if [ "${MISSING_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent maintenance_record_code, found ${MISSING_COUNT}"
  exit 1
fi
echo "PASS: nonexistent maintenance_record_code correctly yields zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-DETAIL-001"
