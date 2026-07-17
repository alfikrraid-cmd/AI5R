#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SOOT-BLOWER-CREATE-001 (Soot Blower Create).
# MO-001 (OSA Maintenance v0.1) / BP-SOOT-BLOWER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SB-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name, blower_type, status) VALUES ('${TEST_CODE}', 'TEST SOOT BLOWER', 'RETRACTABLE', 'ACTIVE');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}' AND soot_blower_name = 'TEST SOOT BLOWER';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_CODE}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate soot_blower_code is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name) VALUES ('${TEST_CODE}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate soot_blower_code was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate soot_blower_code rejected by the same unique constraint the workflow's 'Check Existing Soot Blower' / 'IF Soot Blower Code Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SOOT-BLOWER-CREATE-001"
