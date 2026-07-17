#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-UPDATE-001
# (Interchange Compatibility Update). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_A="TEST-SEAL-IC-UPDATE-A-$$"
TEST_SEAL_B="TEST-SEAL-IC-UPDATE-B-$$"
TEST_SEAL_C="TEST-SEAL-IC-UPDATE-C-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code IN ('${TEST_SEAL_A}', '${TEST_SEAL_B}', '${TEST_SEAL_C}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] One seal with two interchange rows: one to update, one control"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_A}', 'TEST SEAL A'), ('${TEST_SEAL_B}', 'TEST SEAL B'), ('${TEST_SEAL_C}', 'TEST SEAL C');"
psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code, notes) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_B}', 'before update');"
psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code, notes) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_C}', 'untouched');"

echo "[1/2] Valid update (mirrors 'Update Interchange Compatibility's UPDATE ... SET notes = ...) modifies only the targeted composite-key row"
psql_run -c "UPDATE seal_interchange_compatibility SET notes = 'after update' WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = '${TEST_SEAL_B}';"

UPDATED_NOTES=$(psql_run -tAc "SELECT notes FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = '${TEST_SEAL_B}';")
OTHER_NOTES=$(psql_run -tAc "SELECT notes FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = '${TEST_SEAL_C}';")

if [ "${UPDATED_NOTES}" != "after update" ]; then
  echo "FAIL: expected notes 'after update' on targeted row, got '${UPDATED_NOTES}'"
  exit 1
fi
if [ "${OTHER_NOTES}" != "untouched" ]; then
  echo "FAIL: unrelated row was modified (notes now '${OTHER_NOTES}')"
  exit 1
fi
echo "PASS: only the targeted composite-key row changed; the other interchange row is untouched"

echo "[2/2] Unknown composite key updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE seal_interchange_compatibility SET notes = 'x' WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = 'DOES-NOT-EXIST-$$' RETURNING seal_code;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent composite key"
  exit 1
fi
echo "PASS: nonexistent composite key affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-UPDATE-001"
