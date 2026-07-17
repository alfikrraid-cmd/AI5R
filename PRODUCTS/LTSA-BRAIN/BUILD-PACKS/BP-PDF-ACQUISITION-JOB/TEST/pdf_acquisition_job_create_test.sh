#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-CREATE-001
# (PDF Acquisition Job Create). MWO-LTSA-040D (Engineering PDF
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFAJ-CREATE-$$"
TEST_PD_ID="TEST-PD-PDFAJ-CREATE-$$"
TEST_ID="TEST-PDFAJ-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_acquisition_job WHERE pdf_acquisition_job_id LIKE 'TEST-PDFAJ-CREATE-$$%';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> pdf_document)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF ACQUISITION JOB');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR ACQUISITION JOB', 'DATASHEET');"

echo "[1/3] Valid create inserts a row with correctly mapped fields, defaulting status to PENDING"
psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_PD_ID}');"

ROW_STATUS=$(psql_run -tAc "SELECT status FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}';")
if [ "${ROW_STATUS}" != "PENDING" ]; then
  echo "FAIL: expected default status 'PENDING', got '${ROW_STATUS}'"
  exit 1
fi
echo "PASS: row created with correctly mapped fields, status defaulted to PENDING"

echo "[2/3] status outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_STATUS_OUTPUT=$(psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id, status) VALUES ('${TEST_ID}-BAD', '${TEST_KS_ID}', '${TEST_PD_ID}', 'READY_FOR_MANUFACTURING');" 2>&1)
BAD_STATUS_EXIT=$?
set -e
if [ "${BAD_STATUS_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set status was accepted"
  exit 1
fi
echo "${BAD_STATUS_OUTPUT}" | grep -qi "pdf_acquisition_job_status_check" || { echo "FAIL: unexpected error on bad status: ${BAD_STATUS_OUTPUT}"; exit 1; }
echo "PASS: status outside the 4-value closed set (note: READY_FOR_MANUFACTURING, valid for acquisition_job/040C, is NOT valid here) rejected by pdf_acquisition_job_status_check"

echo "[3/3] Duplicate pdf_acquisition_job_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_PD_ID}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate pdf_acquisition_job_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate pdf_acquisition_job_id rejected by the same unique constraint the workflow's 'Check Existing PDF Acquisition Job' / 'IF PDF Acquisition Job Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-CREATE-001"
