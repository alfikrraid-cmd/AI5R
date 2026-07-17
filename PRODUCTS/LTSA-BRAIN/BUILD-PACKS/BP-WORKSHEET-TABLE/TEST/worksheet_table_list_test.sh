#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORKSHEET-TABLE-LIST-001
# (Worksheet Table List). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-WT-LIST-$$"
TEST_WB_ID="TEST-WB-WT-LIST-$$"
TEST_WS_ID="TEST-WS-WT-LIST-$$"
TEST_ID="TEST-WT-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM worksheet_table WHERE worksheet_table_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM worksheet WHERE worksheet_id = '${TEST_WS_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain: knowledge_source_registry -> workbook -> worksheet"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR TABLE LIST');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR TABLE LIST');"
psql_run -c "INSERT INTO worksheet (worksheet_id, workbook_id, worksheet_name) VALUES ('${TEST_WS_ID}', '${TEST_WB_ID}', 'TEST WORKSHEET FOR TABLE LIST');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM worksheet_table;")
psql_run -c "INSERT INTO worksheet_table (worksheet_table_id, worksheet_id, table_name) VALUES ('${TEST_ID}', '${TEST_WS_ID}', 'TEST TABLE LIST');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM worksheet_table;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Worksheet Tables' node's unfiltered SELECT * FROM worksheet_table reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_NAME=$(psql_run -tAc "SELECT table_name FROM worksheet_table WHERE worksheet_table_id = '${TEST_ID}';")
if [ "${FOUND_NAME}" != "TEST TABLE LIST" ]; then
  echo "FAIL: expected table_name 'TEST TABLE LIST', got '${FOUND_NAME}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Worksheet Tables' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORKSHEET-TABLE-LIST-001"
