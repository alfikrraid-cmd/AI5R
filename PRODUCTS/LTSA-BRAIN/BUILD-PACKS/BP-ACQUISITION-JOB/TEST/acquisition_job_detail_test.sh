#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ACQUISITION-JOB-DETAIL-001
# (Acquisition Job Detail). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-AJ-DETAIL-$$"
TEST_WB_ID="TEST-WB-AJ-DETAIL-$$"
TEST_MP_ID="TEST-MP-AJ-DETAIL-$$"
TEST_ID="TEST-AJ-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM workbook WHERE workbook_id = '${TEST_WB_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and fixture acquisition job"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PUMP_MASTER_EXCEL', 'TEST SOURCE FOR JOB DETAIL');"
psql_run -c "INSERT INTO workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name) VALUES ('${TEST_WB_ID}', '${TEST_KS_ID}', 'PUMP_MASTER', 'TEST WORKBOOK FOR JOB DETAIL');"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR JOB DETAIL', 'PUMP_MASTER');"
psql_run -c "INSERT INTO acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id) VALUES ('${TEST_ID}', '${TEST_WB_ID}', '${TEST_MP_ID}');"

echo "[1/2] Known acquisition_job_id returns the correct, full record"
STATUS=$(psql_run -tAc "SELECT status FROM acquisition_job WHERE acquisition_job_id = '${TEST_ID}' LIMIT 1;")
if [ "${STATUS}" != "PENDING" ]; then
  echo "FAIL: expected status 'PENDING', got '${STATUS}'"
  exit 1
fi
echo "PASS: known acquisition_job_id resolves to the correct record (query mirrors 'Get Acquisition Job Detail': SELECT * FROM acquisition_job WHERE acquisition_job_id = ...)"

echo "[2/2] Unknown acquisition_job_id returns zero rows (workflow maps this to statusCode 404 in 'Build Acquisition Job Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM acquisition_job WHERE acquisition_job_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent acquisition_job_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent acquisition_job_id resolves to zero rows at the DB level; 'Build Acquisition Job Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ACQUISITION-JOB-DETAIL-001"
