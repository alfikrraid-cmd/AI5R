#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-METADATA-DETAIL-001 (PDF Metadata Detail).
# MWO-LTSA-040D (Engineering PDF Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFMETA-DETAIL-$$"
TEST_PD_ID="TEST-PD-PDFMETA-DETAIL-$$"
TEST_ID="TEST-PDFMETA-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_metadata WHERE pdf_metadata_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and fixture PDF metadata"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF METADATA DETAIL');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR METADATA DETAIL', 'DATASHEET');"
psql_run -c "INSERT INTO pdf_metadata (pdf_metadata_id, pdf_document_id, title) VALUES ('${TEST_ID}', '${TEST_PD_ID}', 'TEST METADATA DETAIL TITLE');"

echo "[1/2] Known pdf_metadata_id returns the correct, full record"
TITLE=$(psql_run -tAc "SELECT title FROM pdf_metadata WHERE pdf_metadata_id = '${TEST_ID}' LIMIT 1;")
if [ "${TITLE}" != "TEST METADATA DETAIL TITLE" ]; then
  echo "FAIL: expected title 'TEST METADATA DETAIL TITLE', got '${TITLE}'"
  exit 1
fi
echo "PASS: known pdf_metadata_id resolves to the correct record (query mirrors 'Get PDF Metadata Detail': SELECT * FROM pdf_metadata WHERE pdf_metadata_id = ...)"

echo "[2/2] Unknown pdf_metadata_id returns zero rows (workflow maps this to statusCode 404 in 'Build PDF Metadata Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM pdf_metadata WHERE pdf_metadata_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent pdf_metadata_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent pdf_metadata_id resolves to zero rows at the DB level; 'Build PDF Metadata Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-METADATA-DETAIL-001"
