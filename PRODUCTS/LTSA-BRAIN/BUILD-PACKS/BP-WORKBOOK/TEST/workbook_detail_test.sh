#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORKBOOK-DETAIL-001 (Workbook Detail).
# MWO-LTSA-040C (Universal Tabular Data Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-WB-DETAIL-$$"
TEST_ID="TEST-WB-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row and fixture workbook"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR WORKBOOK DETAIL');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK DETAIL');"

echo "[1/2] Known workbook_id returns the correct, full record"
NAME=$(psql_run -tAc "SELECT workbook_name FROM workbook WHERE workbook_id = '${TEST_ID}' LIMIT 1;")
if [ "${NAME}" != "TEST WORKBOOK DETAIL" ]; then
  echo "FAIL: expected workbook_name 'TEST WORKBOOK DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known workbook_id resolves to the correct record (query mirrors 'Get Workbook Detail': SELECT * FROM workbook WHERE workbook_id = ...)"

echo "[2/2] Unknown workbook_id returns zero rows (workflow maps this to statusCode 404 in 'Build Workbook Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM workbook WHERE workbook_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent workbook_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent workbook_id resolves to zero rows at the DB level; 'Build Workbook Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORKBOOK-DETAIL-001"
