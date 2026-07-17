#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-STOCK-DELETE-001 (Seal Stock Delete).
# MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
#
# Uses a record created and destroyed solely within this test (not shared
# with seal_stock_detail_test.sh / seal_stock_update_test.sh fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-STOCK-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_stock WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'TEST SEAL FOR STOCK DELETE');"
psql_run -c "INSERT INTO seal_stock (seal_code, quantity_on_hand) VALUES ('${TEST_CODE}', 2);"

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal"
psql_run -c "DELETE FROM seal_stock WHERE seal_code = '${TEST_CODE}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM seal_stock WHERE seal_code = '${TEST_CODE}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this seal_code would now return 404"

echo "[2/2] Unknown seal_code deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM seal_stock WHERE seal_code = 'DOES-NOT-EXIST-$$' RETURNING seal_code;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent seal_code"
  exit 1
fi
echo "PASS: nonexistent seal_code affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-STOCK-DELETE-001"
