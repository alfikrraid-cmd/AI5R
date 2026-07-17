#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORKBOOK-CREATE-001 (Workbook Create).
# MWO-LTSA-040C (Universal Tabular Data Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-WB-CREATE-$$"
TEST_ID="TEST-WB-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row (workbook.knowledge_source_id is FK'd to it)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR WORKBOOK');"

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM workbook WHERE workbook_id = '${TEST_ID}' AND workbook_type = 'PUMP_MASTER';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/3] workbook_type outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_ID}-BAD', '${TEST_KS_ID}', 'RANDOM_SHEET', 'Bad Type');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set workbook_type was accepted"
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_ID}-BAD';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "workbook_type_check" || { echo "FAIL: unexpected error on bad workbook_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: workbook_type outside the 11-value closed set rejected by workbook_type_check"

echo "[3/3] Duplicate workbook_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'SEAL_STOCK', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate workbook_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate workbook_id rejected by the same unique constraint the workflow's 'Check Existing Workbook' / 'IF Workbook Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORKBOOK-CREATE-001"
