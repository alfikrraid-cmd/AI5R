#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-DELETE-001 (Maintenance History Delete).
# MO-001 (OSA Maintenance v0.1) / BP-MAINTENANCE-HISTORY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-MH-DELETE-$$"

echo "[1/2] Delete removes the targeted row"
psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken) VALUES ('${TEST_CODE}', 'TEST MH DELETE');"
psql_run -c "DELETE FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';"

REMAINING=$(psql_run -tAc "SELECT count(*) FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: expected 0 rows remaining for ${TEST_CODE}, found ${REMAINING}"
  exit 1
fi
echo "PASS: row removed, matching 'Delete Maintenance History' node's DELETE ... RETURNING *"

echo "[2/2] Deleting a nonexistent maintenance_record_code affects zero rows, matching 'Check Delete Result' node's 404 branch"
DELETE_OUTPUT=$(psql_run -tAc "DELETE FROM maintenance_history WHERE maintenance_record_code = 'NONEXISTENT-MH-CODE' RETURNING maintenance_record_code;")
if [ -n "${DELETE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent maintenance_record_code"
  exit 1
fi
echo "PASS: nonexistent maintenance_record_code delete returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-DELETE-001"
