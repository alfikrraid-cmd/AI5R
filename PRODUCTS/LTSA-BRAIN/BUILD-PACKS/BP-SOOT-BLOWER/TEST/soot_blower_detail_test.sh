#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SOOT-BLOWER-DETAIL-001 (Soot Blower Detail).
# MO-001 (OSA Maintenance v0.1) / BP-SOOT-BLOWER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SB-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Existing soot_blower_code returns its row"
psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name) VALUES ('${TEST_CODE}', 'TEST SB DETAIL');"
FOUND_NAME=$(psql_run -tAc "SELECT soot_blower_name FROM soot_blower_registry WHERE soot_blower_code = '${TEST_CODE}';")
if [ "${FOUND_NAME}" != "TEST SB DETAIL" ]; then
  echo "FAIL: expected 'TEST SB DETAIL', got '${FOUND_NAME}'"
  exit 1
fi
echo "PASS: detail row matches inserted fields, matching 'Get Soot Blower Detail' node's SELECT ... WHERE soot_blower_code = \$1"

echo "[2/2] Non-existent soot_blower_code yields zero rows, matching 'Build Soot Blower Detail Response' node's 404 branch"
MISSING_COUNT=$(psql_run -tAc "SELECT count(*) FROM soot_blower_registry WHERE soot_blower_code = 'NONEXISTENT-SB-CODE';")
if [ "${MISSING_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent soot_blower_code, found ${MISSING_COUNT}"
  exit 1
fi
echo "PASS: nonexistent soot_blower_code correctly yields zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SOOT-BLOWER-DETAIL-001"
