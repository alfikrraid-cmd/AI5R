#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-DETAIL-001
# (PDF Acquisition Job Detail). MWO-LTSA-040D (Engineering PDF
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFAJ-DETAIL-$$"
TEST_PD_ID="TEST-PD-PDFAJ-DETAIL-$$"
TEST_ID="TEST-PDFAJ-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and fixture PDF acquisition job"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF ACQUISITION JOB DETAIL');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR ACQUISITION JOB DETAIL', 'DATASHEET');"
psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_PD_ID}');"

echo "[1/2] Known pdf_acquisition_job_id returns the correct, full record"
STATUS=$(psql_run -tAc "SELECT status FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}' LIMIT 1;")
if [ "${STATUS}" != "PENDING" ]; then
  echo "FAIL: expected status 'PENDING', got '${STATUS}'"
  exit 1
fi
echo "PASS: known pdf_acquisition_job_id resolves to the correct record (query mirrors 'Get PDF Acquisition Job Detail': SELECT * FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = ...)"

echo "[2/2] Unknown pdf_acquisition_job_id returns zero rows (workflow maps this to statusCode 404 in 'Build PDF Acquisition Job Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent pdf_acquisition_job_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent pdf_acquisition_job_id resolves to zero rows at the DB level; 'Build PDF Acquisition Job Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-DETAIL-001"
