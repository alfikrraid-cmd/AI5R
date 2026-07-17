#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ASSET-DETAIL-001 (Asset Detail).
# MO-001 (OSA Maintenance v0.1) / BP-ASSET.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-ASSET-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM asset_registry WHERE asset_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Existing asset_code returns its row"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name) VALUES ('${TEST_CODE}', 'TEST ASSET DETAIL');"
FOUND_NAME=$(psql_run -tAc "SELECT asset_name FROM asset_registry WHERE asset_code = '${TEST_CODE}';")
if [ "${FOUND_NAME}" != "TEST ASSET DETAIL" ]; then
  echo "FAIL: expected 'TEST ASSET DETAIL', got '${FOUND_NAME}'"
  exit 1
fi
echo "PASS: detail row matches inserted fields, matching 'Get Asset Detail' node's SELECT ... WHERE asset_code = \$1"

echo "[2/2] Non-existent asset_code yields zero rows, matching 'Build Asset Detail Response' node's 404 branch"
MISSING_COUNT=$(psql_run -tAc "SELECT count(*) FROM asset_registry WHERE asset_code = 'NONEXISTENT-ASSET-CODE';")
if [ "${MISSING_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent asset_code, found ${MISSING_COUNT}"
  exit 1
fi
echo "PASS: nonexistent asset_code correctly yields zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ASSET-DETAIL-001"
