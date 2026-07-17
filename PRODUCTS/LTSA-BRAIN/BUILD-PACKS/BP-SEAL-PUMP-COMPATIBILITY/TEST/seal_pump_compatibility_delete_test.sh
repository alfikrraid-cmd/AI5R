#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-DELETE-001
# (Pump Compatibility Delete). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
#
# Uses records created and destroyed solely within this test (not shared
# with seal_pump_compatibility_detail_test.sh / _update_test.sh fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-PC-DELETE-$$"
TEST_TAG="TEST-PUMP-PC-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR PUMP COMPATIBILITY DELETE');"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'TEST-AREA');"
psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number) VALUES ('${TEST_SEAL_CODE}', '${TEST_TAG}');"

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal"
psql_run -c "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this composite key would now return 404"

echo "[2/2] Unknown composite key deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = 'DOES-NOT-EXIST-$$' RETURNING seal_code;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent composite key"
  exit 1
fi
echo "PASS: nonexistent composite key affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-DELETE-001"
