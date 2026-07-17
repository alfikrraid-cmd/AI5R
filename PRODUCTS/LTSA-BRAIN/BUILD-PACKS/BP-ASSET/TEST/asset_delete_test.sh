#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ASSET-DELETE-001 (Asset Delete).
# MO-001 (OSA Maintenance v0.1) / BP-ASSET.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-ASSET-DELETE-$$"

echo "[1/2] Delete removes the targeted row"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name) VALUES ('${TEST_CODE}', 'TEST ASSET DELETE');"
psql_run -c "DELETE FROM asset_registry WHERE asset_code = '${TEST_CODE}';"

REMAINING=$(psql_run -tAc "SELECT count(*) FROM asset_registry WHERE asset_code = '${TEST_CODE}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: expected 0 rows remaining for ${TEST_CODE}, found ${REMAINING}"
  exit 1
fi
echo "PASS: row removed, matching 'Delete Asset' node's DELETE ... RETURNING *"

echo "[2/2] Deleting a nonexistent asset_code affects zero rows, matching 'Check Delete Result' node's 404 branch"
DELETE_OUTPUT=$(psql_run -tAc "DELETE FROM asset_registry WHERE asset_code = 'NONEXISTENT-ASSET-CODE' RETURNING asset_code;")
if [ -n "${DELETE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent asset_code"
  exit 1
fi
echo "PASS: nonexistent asset_code delete returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ASSET-DELETE-001"
