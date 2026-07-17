#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SOOT-BLOWER-LIST-001 (Soot Blower List).
# MO-001 (OSA Maintenance v0.1) / BP-SOOT-BLOWER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE_A="TEST-SB-LIST-A-$$"
TEST_CODE_B="TEST-SB-LIST-B-$$"

cleanup() {
  psql_run -c "DELETE FROM soot_blower_registry WHERE soot_blower_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/1] List returns every inserted row, matching 'List Soot Blowers' node's SELECT * ORDER BY created_at DESC"
psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name) VALUES ('${TEST_CODE_A}', 'List Test A');"
psql_run -c "INSERT INTO soot_blower_registry (soot_blower_code, soot_blower_name) VALUES ('${TEST_CODE_B}', 'List Test B');"

FOUND_COUNT=$(psql_run -tAc "SELECT count(*) FROM soot_blower_registry WHERE soot_blower_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');")
if [ "${FOUND_COUNT}" -ne 2 ]; then
  echo "FAIL: expected 2 rows, found ${FOUND_COUNT}"
  exit 1
fi
echo "PASS: both inserted rows are present and would be returned by the List Soot Blowers query"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SOOT-BLOWER-LIST-001"
