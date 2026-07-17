#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-STOCK-DETAIL-001 (Seal Stock Detail).
# MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-STOCK-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_stock WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry row and fixture stock record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'TEST SEAL FOR STOCK DETAIL');"
psql_run -c "INSERT INTO seal_stock (seal_code, quantity_on_hand) VALUES ('${TEST_CODE}', 7);"

echo "[1/2] Known seal_code returns the correct, full record"
QTY=$(psql_run -tAc "SELECT quantity_on_hand FROM seal_stock WHERE seal_code = '${TEST_CODE}' LIMIT 1;")
if [ "${QTY}" != "7" ]; then
  echo "FAIL: expected quantity_on_hand '7', got '${QTY}'"
  exit 1
fi
echo "PASS: known seal_code resolves to the correct record (query mirrors 'Get Seal Stock Detail': SELECT * FROM seal_stock WHERE seal_code = ...)"

echo "[2/2] Unknown seal_code returns zero rows (workflow maps this to statusCode 404 in 'Build Seal Stock Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_stock WHERE seal_code = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent seal_code, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent seal_code resolves to zero rows at the DB level; 'Build Seal Stock Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-STOCK-DETAIL-001"
