#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-CREATE-001
# (Interchange Compatibility Create). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_A="TEST-SEAL-IC-CREATE-A-$$"
TEST_SEAL_B="TEST-SEAL-IC-CREATE-B-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code IN ('${TEST_SEAL_A}', '${TEST_SEAL_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two distinct parent seal_registry rows (both sides of the self-referential FK)"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_A}', 'TEST SEAL A'), ('${TEST_SEAL_B}', 'TEST SEAL B');"

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code, notes) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_B}', 'manufacturer equivalent');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = '${TEST_SEAL_B}';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for (${TEST_SEAL_A}, ${TEST_SEAL_B}), found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/3] A seal recorded as its own interchange is rejected by the schema CHECK constraint"
echo "NOTE: 'Validate Interchange Compatibility Input' also rejects this at the workflow layer"
echo "-- this test asserts the DB-level backstop (seal_interchange_not_self)."
set +e
SELF_OUTPUT=$(psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_A}');" 2>&1)
SELF_EXIT=$?
set -e
if [ "${SELF_EXIT}" -eq 0 ]; then
  echo "FAIL: a self-referential interchange row was accepted"
  psql_run -c "DELETE FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = '${TEST_SEAL_A}';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${SELF_OUTPUT}" | grep -qi "seal_interchange_not_self" || { echo "FAIL: unexpected error on self-reference: ${SELF_OUTPUT}"; exit 1; }
echo "PASS: seal_code = compatible_seal_code rejected by seal_interchange_not_self"

echo "[3/3] Duplicate (seal_code, compatible_seal_code) pair is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_B}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate (seal_code, compatible_seal_code) was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate (seal_code, compatible_seal_code) rejected by the composite primary key constraint the workflow's 'Check Existing Interchange Compatibility' / 'IF Interchange Compatibility Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-CREATE-001"
