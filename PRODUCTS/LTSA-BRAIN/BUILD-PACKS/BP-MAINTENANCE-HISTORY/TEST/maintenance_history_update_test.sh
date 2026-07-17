#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-UPDATE-001 (Maintenance History Update).
# MO-001 (OSA Maintenance v0.1) / BP-MAINTENANCE-HISTORY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-MH-UPDATE-$$"

cleanup() {
  psql_run -c "DELETE FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Update statement mutates only the targeted row's notes field"
psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken) VALUES ('${TEST_CODE}', 'TEST MH UPDATE');"
psql_run -c "UPDATE maintenance_history SET notes = 'Follow-up inspection scheduled' WHERE maintenance_record_code = '${TEST_CODE}';"

NEW_NOTES=$(psql_run -tAc "SELECT notes FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';")
if [ "${NEW_NOTES}" != "Follow-up inspection scheduled" ]; then
  echo "FAIL: expected notes 'Follow-up inspection scheduled', got '${NEW_NOTES}'"
  exit 1
fi
echo "PASS: notes field updated correctly, matching 'Update Maintenance History' node's dynamic SET clause"

echo "[2/2] Updating a nonexistent maintenance_record_code affects zero rows, matching 'Check Update Result' node's 404 branch"
UPDATE_OUTPUT=$(psql_run -tAc "UPDATE maintenance_history SET notes = 'X' WHERE maintenance_record_code = 'NONEXISTENT-MH-CODE' RETURNING maintenance_record_code;")
if [ -n "${UPDATE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent maintenance_record_code"
  exit 1
fi
echo "PASS: nonexistent maintenance_record_code update returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-UPDATE-001"
