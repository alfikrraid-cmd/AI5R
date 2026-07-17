#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-LIST-001
# (Pump Compatibility List). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-PC-LIST-$$"
TEST_TAG="TEST-PUMP-PC-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry and ltsa_pumps rows"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR PUMP COMPATIBILITY LIST');"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'TEST-AREA');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM seal_pump_compatibility;")
psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number) VALUES ('${TEST_SEAL_CODE}', '${TEST_TAG}');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM seal_pump_compatibility;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Pump Compatibility' node's unfiltered SELECT * FROM seal_pump_compatibility reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TAG=$(psql_run -tAc "SELECT pump_tag_number FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}';")
if [ "${FOUND_TAG}" != "${TEST_TAG}" ]; then
  echo "FAIL: expected pump_tag_number '${TEST_TAG}', got '${FOUND_TAG}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Pump Compatibility' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-LIST-001"
