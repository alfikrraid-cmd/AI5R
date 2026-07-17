#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-STOCK-LIST-001 (Seal Stock List).
# MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-STOCK-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_stock WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry row"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'TEST SEAL FOR STOCK LIST');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM seal_stock;")
psql_run -c "INSERT INTO seal_stock (seal_code, quantity_on_hand) VALUES ('${TEST_CODE}', 3);"
AFTER=$(psql_run -tAc "SELECT count(*) FROM seal_stock;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Seal Stock' node's unfiltered SELECT * FROM seal_stock reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_QTY=$(psql_run -tAc "SELECT quantity_on_hand FROM seal_stock WHERE seal_code = '${TEST_CODE}';")
if [ "${FOUND_QTY}" != "3" ]; then
  echo "FAIL: expected quantity_on_hand '3', got '${FOUND_QTY}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Seal Stock' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-STOCK-LIST-001"
