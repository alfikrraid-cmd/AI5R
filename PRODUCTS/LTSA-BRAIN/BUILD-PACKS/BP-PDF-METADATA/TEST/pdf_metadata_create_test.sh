#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-METADATA-CREATE-001 (PDF Metadata Create).
# MWO-LTSA-040D (Engineering PDF Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFMETA-CREATE-$$"
TEST_PD_ID="TEST-PD-PDFMETA-CREATE-$$"
TEST_ID="TEST-PDFMETA-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_metadata WHERE pdf_metadata_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> pdf_document)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF METADATA');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR METADATA', 'DATASHEET');"

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO pdf_metadata (pdf_metadata_id, pdf_document_id, title, author, pdf_version) VALUES ('${TEST_ID}', '${TEST_PD_ID}', 'Test Title', 'Test Author', '1.7');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM pdf_metadata WHERE pdf_metadata_id = '${TEST_ID}' AND title = 'Test Title';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] A second PDF Metadata row for the same pdf_document_id is rejected (one-metadata-per-document, WP-000 design decision 8)"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO pdf_metadata (pdf_metadata_id, pdf_document_id) VALUES ('${TEST_ID}-DUP', '${TEST_PD_ID}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: a second pdf_metadata row for the same pdf_document_id was accepted"
  psql_run -c "DELETE FROM pdf_metadata WHERE pdf_metadata_id = '${TEST_ID}-DUP';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "pdf_metadata_pdf_document_id_unique" || { echo "FAIL: unexpected error on duplicate pdf_document_id: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: second pdf_metadata row for the same pdf_document_id rejected by pdf_metadata_pdf_document_id_unique"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-METADATA-CREATE-001"
