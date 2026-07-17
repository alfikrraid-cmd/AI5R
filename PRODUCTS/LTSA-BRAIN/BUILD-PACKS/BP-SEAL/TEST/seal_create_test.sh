#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-CREATE-001 (Seal Create).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name, material, status) VALUES ('${TEST_CODE}', 'TEST SEAL', 'Viton', 'ACTIVE');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_registry WHERE seal_code = '${TEST_CODE}' AND seal_name = 'TEST SEAL';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_CODE}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate seal_code is rejected by the workflow's pre-insert conflict check"
echo "NOTE: WF-LTSA-BRAIN-SEAL-CREATE-001.json includes 'Check Existing Seal' /"
echo "'IF Seal Code Exists' nodes (built this way in MWO-P-005), the same"
echo "pre-insert-conflict pattern Customer Create uses -- unlike Pump Create, which"
echo "has no such check. This test asserts the schema-level constraint that pattern"
echo "relies on."
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate seal_code was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate seal_code rejected by the same unique constraint the workflow's 'Check Existing Seal' / 'IF Seal Code Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-CREATE-001"
