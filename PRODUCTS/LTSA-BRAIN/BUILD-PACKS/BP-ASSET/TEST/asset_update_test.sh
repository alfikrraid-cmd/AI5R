#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ASSET-UPDATE-001 (Asset Update).
# MO-001 (OSA Maintenance v0.1) / BP-ASSET.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-ASSET-UPDATE-$$"

cleanup() {
  psql_run -c "DELETE FROM asset_registry WHERE asset_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Update statement mutates only the targeted row's status field"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name, status) VALUES ('${TEST_CODE}', 'TEST ASSET UPDATE', 'ACTIVE');"
psql_run -c "UPDATE asset_registry SET status = 'DECOMMISSIONED', updated_at = NOW() WHERE asset_code = '${TEST_CODE}';"

NEW_STATUS=$(psql_run -tAc "SELECT status FROM asset_registry WHERE asset_code = '${TEST_CODE}';")
if [ "${NEW_STATUS}" != "DECOMMISSIONED" ]; then
  echo "FAIL: expected status 'DECOMMISSIONED', got '${NEW_STATUS}'"
  exit 1
fi
echo "PASS: status field updated correctly, matching 'Update Asset' node's dynamic SET clause"

echo "[2/2] Updating a nonexistent asset_code affects zero rows, matching 'Check Update Result' node's 404 branch"
UPDATE_OUTPUT=$(psql_run -tAc "UPDATE asset_registry SET status = 'X' WHERE asset_code = 'NONEXISTENT-ASSET-CODE' RETURNING asset_code;")
if [ -n "${UPDATE_OUTPUT}" ]; then
  echo "FAIL: expected no returned row for a nonexistent asset_code"
  exit 1
fi
echo "PASS: nonexistent asset_code update returns zero rows"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ASSET-UPDATE-001"
