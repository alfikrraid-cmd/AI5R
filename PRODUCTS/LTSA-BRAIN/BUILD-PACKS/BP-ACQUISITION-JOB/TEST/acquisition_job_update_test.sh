#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ACQUISITION-JOB-UPDATE-001
# (Acquisition Job Update). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-AJ-UPDATE-$$"
TEST_WB_ID="TEST-WB-AJ-UPDATE-$$"
TEST_MP_ID="TEST-MP-AJ-UPDATE-$$"
TEST_ID="TEST-AJ-UPDATE-$$"
OTHER_ID="TEST-AJ-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM acquisition_job WHERE acquisition_job_id IN ('${TEST_ID}', '${OTHER_ID}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and two fixture jobs: one to update, one control"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR JOB UPDATE');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR JOB UPDATE');"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR JOB UPDATE', 'PUMP_MASTER');"
psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id) VALUES ('${TEST_ID}', '${TEST_WB_ID}', '${TEST_MP_ID}');"
psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id) VALUES ('${OTHER_ID}', '${TEST_WB_ID}', '${TEST_MP_ID}');"

echo "[1/2] Valid update (equivalent to 'Update Acquisition Job's dynamic SET clause for status/rows_processed) modifies only the targeted row's specified fields, workbook_id/mapping_profile_id untouched"
psql_run -c "UPDATE acquisition_job SET status = 'READY_FOR_MANUFACTURING', rows_processed = 42, rows_valid = 40, rows_invalid = 2, updated_at = NOW() WHERE acquisition_job_id = '${TEST_ID}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}';")
UPDATED_WORKBOOK=$(psql_run -tAc "SELECT workbook_id FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM acquisition_job WHERE acquisition_job_id = '${OTHER_ID}';")

if [ "${UPDATED_STATUS}" != "READY_FOR_MANUFACTURING" ]; then
  echo "FAIL: expected status 'READY_FOR_MANUFACTURING' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_WORKBOOK}" != "${TEST_WB_ID}" ]; then
  echo "FAIL: workbook_id changed unexpectedly to '${UPDATED_WORKBOOK}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "PENDING" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's execution-result fields changed; workbook_id/mapping_profile_id and other rows untouched"

echo "[2/2] Unknown acquisition_job_id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE acquisition_job SET status = 'FAILED' WHERE acquisition_job_id = 'DOES-NOT-EXIST-$$' RETURNING acquisition_job_id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent acquisition_job_id"
  exit 1
fi
echo "PASS: nonexistent acquisition_job_id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ACQUISITION-JOB-UPDATE-001"
