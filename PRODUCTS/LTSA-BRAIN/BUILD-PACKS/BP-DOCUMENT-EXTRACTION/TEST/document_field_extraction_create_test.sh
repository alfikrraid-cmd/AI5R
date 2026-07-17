#!/usr/bin/env bash
# Functional test for document_field_extraction (BP-DOCUMENT-EXTRACTION).
# LTSA-BRAIN Document Upload MVP.
#
# Exercises the table's own schema constraints directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-DOCEXTRACT-$$"
TEST_PDF_ID="TEST-PDFDOC-DOCEXTRACT-$$"
TEST_ID="TEST-DOCEXTRACT-$$"

cleanup() {
  psql_run -c "DELETE FROM document_field_extraction WHERE document_field_extraction_id LIKE 'TEST-DOCEXTRACT-$$%';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PDF_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry + pdf_document rows (reused unmodified, not part of this build pack)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR DOC EXTRACTION');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PDF_ID}', '${TEST_KS_ID}', 'TEST PUMP DATASHEET', 'DATASHEET');"

echo "[1/4] Valid insert with JSONB extracted_fields succeeds"
psql_run -c "INSERT INTO document_field_extraction (document_field_extraction_id, source_document_id, source_document_type, detected_document_type, detected_document_type_confidence, extracted_fields) VALUES ('${TEST_ID}', '${TEST_PDF_ID}', 'PDF', 'PUMP_DATASHEET', 0.92, '{\"pump_manufacturer\": {\"value\": \"ACME\", \"confidence\": 0.95}}'::jsonb);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM document_field_extraction WHERE document_field_extraction_id = '${TEST_ID}' AND status = 'PENDING_REVIEW';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID} with default status PENDING_REVIEW, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created, default status PENDING_REVIEW, JSONB field stored"

echo "[2/4] source_document_type outside {PDF, MEDIA} is rejected"
set +e
BAD_SRC_OUTPUT=$(psql_run -c "INSERT INTO document_field_extraction (document_field_extraction_id, source_document_id, source_document_type, detected_document_type, extracted_fields) VALUES ('${TEST_ID}-BADSRC', '${TEST_PDF_ID}', 'SCAN', 'UNKNOWN', '{}'::jsonb);" 2>&1)
BAD_SRC_EXIT=$?
set -e
if [ "${BAD_SRC_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set source_document_type was accepted"
  exit 1
fi
echo "${BAD_SRC_OUTPUT}" | grep -qi "document_field_extraction_source_type_check" || { echo "FAIL: unexpected error: ${BAD_SRC_OUTPUT}"; exit 1; }
echo "PASS: source_document_type rejected by document_field_extraction_source_type_check"

echo "[3/4] detected_document_type outside the closed set is rejected"
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO document_field_extraction (document_field_extraction_id, source_document_id, source_document_type, detected_document_type, extracted_fields) VALUES ('${TEST_ID}-BADTYPE', '${TEST_PDF_ID}', 'PDF', 'RANDOM_TYPE', '{}'::jsonb);" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set detected_document_type was accepted"
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "document_field_extraction_detected_type_check" || { echo "FAIL: unexpected error: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: detected_document_type rejected by document_field_extraction_detected_type_check"

echo "[4/4] confidence outside [0,1] is rejected"
set +e
BAD_CONF_OUTPUT=$(psql_run -c "INSERT INTO document_field_extraction (document_field_extraction_id, source_document_id, source_document_type, detected_document_type, detected_document_type_confidence, extracted_fields) VALUES ('${TEST_ID}-BADCONF', '${TEST_PDF_ID}', 'PDF', 'UNKNOWN', 1.5, '{}'::jsonb);" 2>&1)
BAD_CONF_EXIT=$?
set -e
if [ "${BAD_CONF_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-range confidence was accepted"
  exit 1
fi
echo "${BAD_CONF_OUTPUT}" | grep -qi "document_field_extraction_confidence_check" || { echo "FAIL: unexpected error: ${BAD_CONF_OUTPUT}"; exit 1; }
echo "PASS: confidence outside [0,1] rejected by document_field_extraction_confidence_check"

echo "ALL DB-LEVEL CHECKS COMPLETE for document_field_extraction"
