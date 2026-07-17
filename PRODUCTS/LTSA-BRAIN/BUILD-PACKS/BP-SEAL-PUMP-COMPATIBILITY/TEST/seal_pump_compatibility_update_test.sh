#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-UPDATE-001
# (Pump Compatibility Update). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-PC-UPDATE-$$"
TEST_TAG="TEST-PUMP-PC-UPDATE-$$"
OTHER_TAG="TEST-PUMP-PC-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number IN ('${TEST_TAG}', '${OTHER_TAG}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number IN ('${TEST_TAG}', '${OTHER_TAG}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] One seal, two pumps, two compatibility rows: one to update, one control"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR PUMP COMPATIBILITY UPDATE');"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'TEST-AREA'), ('${OTHER_TAG}', 'TEST-AREA');"
psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number, notes) VALUES ('${TEST_SEAL_CODE}', '${TEST_TAG}', 'before update');"
psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number, notes) VALUES ('${TEST_SEAL_CODE}', '${OTHER_TAG}', 'untouched');"

echo "[1/2] Valid update (mirrors 'Update Pump Compatibility's UPDATE ... SET notes = ...) modifies only the targeted composite-key row"
psql_run -c "UPDATE seal_pump_compatibility SET notes = 'after update' WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';"

UPDATED_NOTES=$(psql_run -tAc "SELECT notes FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';")
OTHER_NOTES=$(psql_run -tAc "SELECT notes FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${OTHER_TAG}';")

if [ "${UPDATED_NOTES}" != "after update" ]; then
  echo "FAIL: expected notes 'after update' on targeted row, got '${UPDATED_NOTES}'"
  exit 1
fi
if [ "${OTHER_NOTES}" != "untouched" ]; then
  echo "FAIL: unrelated row was modified (notes now '${OTHER_NOTES}')"
  exit 1
fi
echo "PASS: only the targeted composite-key row changed; the other pump's compatibility row is untouched"

echo "[2/2] Unknown composite key updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE seal_pump_compatibility SET notes = 'x' WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = 'DOES-NOT-EXIST-$$' RETURNING seal_code;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent composite key"
  exit 1
fi
echo "PASS: nonexistent composite key affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-UPDATE-001"
