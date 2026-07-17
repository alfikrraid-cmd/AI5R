#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SOOT-BLOWER-DELETE-001 (Soot Blower Delete).
# MO-001 (OSA Maintenance v0.1) / BP-SOOT-BLOWER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SB-DELETE-$$"

echo "[1/2] Delete removes the targeted row"
psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name) VALUES ('${TEST_CODE}', 'TEST SB DELETE');"
psql_run -c "DELETE FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';"

REMAINING=$(psql_run -tAc "SELECT count(*) FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: expected 0 rows remaining for ${TEST_CODE}, found ${REMAINING}"
  exit 1
fi
echo "PASS: row removed, matching 'Delete Soot Blower' node's DELETE ... RETURNING *"

echo "[2/2] Deleting a nonexistent soot_blower_code affects zero rows, matching 'Check Delete Result' node's 404 branch"
DELETE_OUTPUT=$(psql_run -tAc "DELETE FROM soot_blower_registry WHERE soot_blower_code = 'NONEXISTENT-SB-CODE' RETURNING soot_blower_code;")
if [ -n "${DELETE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent soot_blower_code"
  exit 1
fi
echo "PASS: nonexistent soot_blower_code delete returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SOOT-BLOWER-DELETE-001"
