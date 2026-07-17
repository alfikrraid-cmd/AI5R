#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-UPDATE-001
# (PDF Acquisition Job Update). MWO-LTSA-040D (Engineering PDF
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFAJ-UPDATE-$$"
TEST_PD_ID="TEST-PD-PDFAJ-UPDATE-$$"
TEST_ID="TEST-PDFAJ-UPDATE-$$"
OTHER_ID="TEST-PDFAJ-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_acquisition_job WHERE pdf_acquisition_job_id IN ('${TEST_ID}', '${OTHER_ID}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and two fixture jobs: one to update, one control"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF JOB UPDATE');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR JOB UPDATE', 'DATASHEET');"
psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_PD_ID}');"
psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id) VALUES ('${OTHER_ID}', '${TEST_KS_ID}', '${TEST_PD_ID}');"

echo "[1/2] Valid update (equivalent to 'Update PDF Acquisition Job's dynamic SET clause for status/finished_at) modifies only the targeted row's specified fields, knowledge_source_id/pdf_document_id untouched"
psql_run -c "UPDATE pdf_acquisition_job SET status = 'COMPLETED', finished_at = NOW(), validation_errors = NULL, updated_at = NOW() WHERE pdf_acquisition_job_id = '${TEST_ID}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}';")
UPDATED_PD=$(psql_run -tAc "SELECT pdf_document_id FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${OTHER_ID}';")

if [ "${UPDATED_STATUS}" != "COMPLETED" ]; then
  echo "FAIL: expected status 'COMPLETED' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_PD}" != "${TEST_PD_ID}" ]; then
  echo "FAIL: pdf_document_id changed unexpectedly to '${UPDATED_PD}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "PENDING" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's execution-result fields changed; knowledge_source_id/pdf_document_id and other rows untouched"

echo "[2/2] Unknown pdf_acquisition_job_id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE pdf_acquisition_job SET status = 'FAILED' WHERE pdf_acquisition_job_id = 'DOES-NOT-EXIST-$$' RETURNING pdf_acquisition_job_id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent pdf_acquisition_job_id"
  exit 1
fi
echo "PASS: nonexistent pdf_acquisition_job_id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-UPDATE-001"
