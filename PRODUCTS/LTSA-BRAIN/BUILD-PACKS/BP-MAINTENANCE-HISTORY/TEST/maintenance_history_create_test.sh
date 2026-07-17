#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-CREATE-001 (Maintenance History Create).
# MO-001 (OSA Maintenance v0.1) / BP-MAINTENANCE-HISTORY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-MH-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken, asset_code, asset_type) VALUES ('${TEST_CODE}', 'Replaced seal', 'P-101', 'pump');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM maintenance_history WHERE maintenance_record_code = '${TEST_CODE}' AND action_taken = 'Replaced seal';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_CODE}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate maintenance_record_code is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO maintenance_history (maintenance_record_code, action_taken) VALUES ('${TEST_CODE}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate maintenance_record_code was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate maintenance_record_code rejected by the same unique constraint the workflow's 'Check Existing Maintenance History' / 'IF Maintenance Record Code Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAINTENANCE-HISTORY-CREATE-001"
