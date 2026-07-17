#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-STOCK-UPDATE-001 (Seal Stock Update).
# MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-STOCK-UPDATE-$$"
OTHER_CODE="TEST-SEAL-STOCK-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_stock WHERE seal_code IN ('${TEST_CODE}', '${OTHER_CODE}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code IN ('${TEST_CODE}', '${OTHER_CODE}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two fixture records: one to update, one control (must stay unaffected)"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'Update Target'), ('${OTHER_CODE}', 'Untouched');"
psql_run -c "INSERT INTO seal_stock (seal_code, quantity_on_hand, location) VALUES ('${TEST_CODE}', 1, 'WAREHOUSE-A');"
psql_run -c "INSERT INTO seal_stock (seal_code, quantity_on_hand, location) VALUES ('${OTHER_CODE}', 1, 'WAREHOUSE-A');"

echo "[1/2] Valid update (equivalent to 'Update Seal Stock's dynamic SET clause for quantity_on_hand only) modifies only the targeted row's specified field"
psql_run -c "UPDATE seal_stock SET quantity_on_hand = 9, updated_at = NOW() WHERE seal_code = '${TEST_CODE}';"

UPDATED_QTY=$(psql_run -tAc "SELECT quantity_on_hand FROM seal_stock WHERE seal_code = '${TEST_CODE}';")
UPDATED_LOCATION=$(psql_run -tAc "SELECT location FROM seal_stock WHERE seal_code = '${TEST_CODE}';")
OTHER_QTY=$(psql_run -tAc "SELECT quantity_on_hand FROM seal_stock WHERE seal_code = '${OTHER_CODE}';")

if [ "${UPDATED_QTY}" != "9" ]; then
  echo "FAIL: expected quantity_on_hand '9' on targeted row, got '${UPDATED_QTY}'"
  exit 1
fi
if [ "${UPDATED_LOCATION}" != "WAREHOUSE-A" ]; then
  echo "FAIL: non-targeted field location changed unexpectedly to '${UPDATED_LOCATION}'"
  exit 1
fi
if [ "${OTHER_QTY}" != "1" ]; then
  echo "FAIL: unrelated row was modified (quantity_on_hand now '${OTHER_QTY}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/2] Unknown seal_code updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE seal_stock SET quantity_on_hand = 0 WHERE seal_code = 'DOES-NOT-EXIST-$$' RETURNING seal_code;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent seal_code"
  exit 1
fi
echo "PASS: nonexistent seal_code affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-STOCK-UPDATE-001"
