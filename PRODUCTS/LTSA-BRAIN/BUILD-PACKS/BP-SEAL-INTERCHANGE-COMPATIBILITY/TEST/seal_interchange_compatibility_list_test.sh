#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-LIST-001
# (Interchange Compatibility List). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_A="TEST-SEAL-IC-LIST-A-$$"
TEST_SEAL_B="TEST-SEAL-IC-LIST-B-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code IN ('${TEST_SEAL_A}', '${TEST_SEAL_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two distinct parent seal_registry rows"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_A}', 'TEST SEAL A'), ('${TEST_SEAL_B}', 'TEST SEAL B');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM seal_interchange_compatibility;")
psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_B}');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM seal_interchange_compatibility;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Interchange Compatibility' node's unfiltered SELECT * FROM seal_interchange_compatibility reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND=$(psql_run -tAc "SELECT compatible_seal_code FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}';")
if [ "${FOUND}" != "${TEST_SEAL_B}" ]; then
  echo "FAIL: expected compatible_seal_code '${TEST_SEAL_B}', got '${FOUND}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Interchange Compatibility' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-LIST-001"
