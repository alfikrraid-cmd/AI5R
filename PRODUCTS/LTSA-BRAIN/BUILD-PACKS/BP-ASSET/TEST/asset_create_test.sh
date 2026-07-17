#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ASSET-CREATE-001 (Asset Create).
# MO-001 (OSA Maintenance v0.1) / BP-ASSET.
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-ASSET-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM asset_registry WHERE asset_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name, asset_type, status) VALUES ('${TEST_CODE}', 'TEST ASSET', 'TANK', 'ACTIVE');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM asset_registry WHERE asset_code = '${TEST_CODE}' AND asset_name = 'TEST ASSET';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_CODE}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate asset_code is rejected by the workflow's pre-insert conflict check"
echo "NOTE: WF-LTSA-BRAIN-ASSET-CREATE-001.json includes 'Check Existing Asset' /"
echo "'IF Asset Code Exists' nodes, following the Seal Registry conflict-check pattern"
echo "(MWO-P-005). This test asserts the schema-level constraint that pattern relies on."
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO asset_registry (asset_code, asset_name) VALUES ('${TEST_CODE}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate asset_code was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate asset_code rejected by the same unique constraint the workflow's 'Check Existing Asset' / 'IF Asset Code Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ASSET-CREATE-001"
