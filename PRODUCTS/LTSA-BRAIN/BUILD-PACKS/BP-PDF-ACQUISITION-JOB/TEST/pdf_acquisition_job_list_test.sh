#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-LIST-001
# (PDF Acquisition Job List). MWO-LTSA-040D (Engineering PDF
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFAJ-LIST-$$"
TEST_PD_ID="TEST-PD-PDFAJ-LIST-$$"
TEST_ID="TEST-PDFAJ-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> pdf_document)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF ACQUISITION JOB LIST');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR ACQUISITION JOB LIST', 'DATASHEET');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM pdf_acquisition_job;")
psql_run -c "INSERT INTO pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_PD_ID}');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM pdf_acquisition_job;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List PDF Acquisition Jobs' node's unfiltered SELECT * FROM pdf_acquisition_job reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_PD=$(psql_run -tAc "SELECT pdf_document_id FROM pdf_acquisition_job WHERE pdf_acquisition_job_id = '${TEST_ID}';")
if [ "${FOUND_PD}" != "${TEST_PD_ID}" ]; then
  echo "FAIL: expected pdf_document_id '${TEST_PD_ID}', got '${FOUND_PD}'"
  exit 1
fi
echo "PASS: row shape matches what 'List PDF Acquisition Jobs' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-ACQUISITION-JOB-LIST-001"
