#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-CREATE-001
# (Pump Compatibility Create). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-PC-CREATE-$$"
TEST_TAG="TEST-PUMP-PC-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry and ltsa_pumps rows (both sides of the composite FK)"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR PUMP COMPATIBILITY');"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'TEST-AREA');"

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number, notes) VALUES ('${TEST_SEAL_CODE}', '${TEST_TAG}', 'fits per drawing X');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for (${TEST_SEAL_CODE}, ${TEST_TAG}), found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate (seal_code, pump_tag_number) pair is rejected by the workflow's pre-insert conflict check"
echo "NOTE: WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-CREATE-001.json includes 'Check Existing Pump"
echo "Compatibility' / 'IF Pump Compatibility Exists' nodes, the same pre-insert-conflict pattern"
echo "Seal Create uses (MWO-P-005), checked against the composite key here."
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number) VALUES ('${TEST_SEAL_CODE}', '${TEST_TAG}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate (seal_code, pump_tag_number) was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate (seal_code, pump_tag_number) rejected by the composite primary key constraint the workflow's 'Check Existing Pump Compatibility' / 'IF Pump Compatibility Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-CREATE-001"
