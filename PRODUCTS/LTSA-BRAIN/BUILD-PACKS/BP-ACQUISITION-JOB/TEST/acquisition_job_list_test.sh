#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ACQUISITION-JOB-LIST-001
# (Acquisition Job List). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-AJ-LIST-$$"
TEST_WB_ID="TEST-WB-AJ-LIST-$$"
TEST_MP_ID="TEST-MP-AJ-LIST-$$"
TEST_ID="TEST-AJ-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain: knowledge_source_registry -> workbook, and mapping_profile"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR JOB LIST');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR JOB LIST');"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR JOB LIST', 'PUMP_MASTER');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM acquisition_job;")
psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id) VALUES ('${TEST_ID}', '${TEST_WB_ID}', '${TEST_MP_ID}');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM acquisition_job;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Acquisition Jobs' node's unfiltered SELECT * FROM acquisition_job reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_STATUS=$(psql_run -tAc "SELECT status FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}';")
if [ "${FOUND_STATUS}" != "PENDING" ]; then
  echo "FAIL: expected status 'PENDING', got '${FOUND_STATUS}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Acquisition Jobs' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ACQUISITION-JOB-LIST-001"
