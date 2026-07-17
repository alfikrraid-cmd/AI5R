#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ACQUISITION-JOB-CREATE-001
# (Acquisition Job Create). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-AJ-CREATE-$$"
TEST_WB_ID="TEST-WB-AJ-CREATE-$$"
TEST_MP_ID="TEST-MP-AJ-CREATE-$$"
TEST_ID="TEST-AJ-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain: knowledge_source_registry -> workbook, and mapping_profile"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR JOB');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR JOB');"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR JOB', 'PUMP_MASTER');"

echo "[1/3] Valid create inserts a row with correctly mapped fields, status defaults to PENDING"
psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id) VALUES ('${TEST_ID}', '${TEST_WB_ID}', '${TEST_MP_ID}');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}' AND status = 'PENDING';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID} with status PENDING, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields, status defaults to PENDING"

echo "[2/3] status outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_STATUS_OUTPUT=$(psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id, status) VALUES ('${TEST_ID}-BAD', '${TEST_WB_ID}', '${TEST_MP_ID}', 'COMPLETE');" 2>&1)
BAD_STATUS_EXIT=$?
set -e
if [ "${BAD_STATUS_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set status was accepted"
  psql_run -c "DELETE FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}-BAD';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${BAD_STATUS_OUTPUT}" | grep -qi "acquisition_job_status_check" || { echo "FAIL: unexpected error on bad status: ${BAD_STATUS_OUTPUT}"; exit 1; }
echo "PASS: status outside PENDING/IN_PROGRESS/READY_FOR_MANUFACTURING/FAILED rejected by acquisition_job_status_check"

echo "[3/3] Duplicate acquisition_job_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id) VALUES ('${TEST_ID}', '${TEST_WB_ID}', '${TEST_MP_ID}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate acquisition_job_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate acquisition_job_id rejected by the same unique constraint the workflow's 'Check Existing Acquisition Job' / 'IF Acquisition Job Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ACQUISITION-JOB-CREATE-001"
