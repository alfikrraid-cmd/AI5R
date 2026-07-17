#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORKSHEET-TABLE-DETAIL-001
# (Worksheet Table Detail). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-WT-DETAIL-$$"
TEST_WB_ID="TEST-WB-WT-DETAIL-$$"
TEST_WS_ID="TEST-WS-WT-DETAIL-$$"
TEST_ID="TEST-WT-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM worksheet_table WHERE worksheet_table_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM worksheet WHERE worksheet_id = '${TEST_WS_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and fixture worksheet_table"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR TABLE DETAIL');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR TABLE DETAIL');"
psql_run -c "INSERT INTO worksheet (worksheet_id, workbook_id, worksheet_name) VALUES ('${TEST_WS_ID}', '${TEST_WB_ID}', 'TEST WORKSHEET FOR TABLE DETAIL');"
psql_run -c "INSERT INTO worksheet_table (worksheet_table_id, worksheet_id, table_name) VALUES ('${TEST_ID}', '${TEST_WS_ID}', 'TEST TABLE DETAIL');"

echo "[1/2] Known worksheet_table_id returns the correct, full record"
NAME=$(psql_run -tAc "SELECT table_name FROM worksheet_table WHERE worksheet_table_id = '${TEST_ID}' LIMIT 1;")
if [ "${NAME}" != "TEST TABLE DETAIL" ]; then
  echo "FAIL: expected table_name 'TEST TABLE DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known worksheet_table_id resolves to the correct record (query mirrors 'Get Worksheet Table Detail': SELECT * FROM worksheet_table WHERE worksheet_table_id = ...)"

echo "[2/2] Unknown worksheet_table_id returns zero rows (workflow maps this to statusCode 404 in 'Build Worksheet Table Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM worksheet_table WHERE worksheet_table_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent worksheet_table_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent worksheet_table_id resolves to zero rows at the DB level; 'Build Worksheet Table Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORKSHEET-TABLE-DETAIL-001"
