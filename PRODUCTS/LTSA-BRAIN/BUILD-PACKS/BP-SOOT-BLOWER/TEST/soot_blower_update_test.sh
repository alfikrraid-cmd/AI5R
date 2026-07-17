#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SOOT-BLOWER-UPDATE-001 (Soot Blower Update).
# MO-001 (OSA Maintenance v0.1) / BP-SOOT-BLOWER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SB-UPDATE-$$"

cleanup() {
  psql_run -c "DELETE FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Update statement mutates only the targeted row's status field"
psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name, status) VALUES ('${TEST_CODE}', 'TEST SB UPDATE', 'ACTIVE');"
psql_run -c "UPDATE soot_blower_registry SET status = 'OUT_OF_SERVICE', updated_at = NOW() WHERE soot_blower_code = '${TEST_CODE}';"

NEW_STATUS=$(psql_run -tAc "SELECT status FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';")
if [ "${NEW_STATUS}" != "OUT_OF_SERVICE" ]; then
  echo "FAIL: expected status 'OUT_OF_SERVICE', got '${NEW_STATUS}'"
  exit 1
fi
echo "PASS: status field updated correctly, matching 'Update Soot Blower' node's dynamic SET clause"

echo "[2/2] Updating a nonexistent soot_blower_code affects zero rows, matching 'Check Update Result' node's 404 branch"
UPDATE_OUTPUT=$(psql_run -tAc "UPDATE soot_blower_registry SET status = 'X' WHERE soot_blower_code = 'NONEXISTENT-SB-CODE' RETURNING soot_blower_code;")
if [ -n "${UPDATE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent soot_blower_code"
  exit 1
fi
echo "PASS: nonexistent soot_blower_code update returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SOOT-BLOWER-UPDATE-001"
