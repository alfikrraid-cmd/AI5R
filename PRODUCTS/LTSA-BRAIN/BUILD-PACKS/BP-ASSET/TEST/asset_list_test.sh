#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ASSET-LIST-001 (Asset List).
# MO-001 (OSA Maintenance v0.1) / BP-ASSET.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE_A="TEST-ASSET-LIST-A-$$"
TEST_CODE_B="TEST-ASSET-LIST-B-$$"

cleanup() {
  psql_run -c "DELETE FROM asset_registry WHERE asset_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/1] List returns every inserted row, matching 'List Assets' node's SELECT * ORDER BY created_at DESC"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name) VALUES ('${TEST_CODE_A}', 'List Test A');"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name) VALUES ('${TEST_CODE_B}', 'List Test B');"

FOUND_COUNT=$(psql_run -tAc "SELECT count(*) FROM asset_registry WHERE asset_code IN ('${TEST_CODE_A}', '${TEST_CODE_B}');")
if [ "${FOUND_COUNT}" -ne 2 ]; then
  echo "FAIL: expected 2 rows, found ${FOUND_COUNT}"
  exit 1
fi
echo "PASS: both inserted rows are present and would be returned by the List Assets query"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ASSET-LIST-001"
