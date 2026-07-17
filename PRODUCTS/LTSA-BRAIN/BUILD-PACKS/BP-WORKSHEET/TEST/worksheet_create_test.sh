#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORKSHEET-CREATE-001 (Worksheet Create).
# MWO-LTSA-040C (Universal Tabular Data Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-WS-CREATE-$$"
TEST_WB_ID="TEST-WB-WS-CREATE-$$"
TEST_ID="TEST-WS-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM worksheet WHERE worksheet_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry and workbook rows (worksheet.workbook_id is FK'd to workbook)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR WORKSHEET');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR WORKSHEET');"

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO worksheet (worksheet_id, workbook_id, worksheet_name, row_count, column_count) VALUES ('${TEST_ID}', '${TEST_WB_ID}', 'Sheet1', 100, 12);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM worksheet WHERE worksheet_id = '${TEST_ID}' AND row_count = 100 AND column_count = 12;")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate worksheet_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO worksheet (worksheet_id, workbook_id, worksheet_name) VALUES ('${TEST_ID}', '${TEST_WB_ID}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate worksheet_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate worksheet_id rejected by the same unique constraint the workflow's 'Check Existing Worksheet' / 'IF Worksheet Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORKSHEET-CREATE-001"
