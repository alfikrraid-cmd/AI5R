#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-DOCUMENT-DETAIL-001 (PDF Document Detail).
# MWO-LTSA-040D (Engineering PDF Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFDOC-DETAIL-$$"
TEST_ID="TEST-PDFDOC-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row and fixture PDF document"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF DOCUMENT DETAIL');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT DETAIL', 'DATASHEET');"

echo "[1/2] Known pdf_document_id returns the correct, full record"
NAME=$(psql_run -tAc "SELECT document_name FROM pdf_document WHERE pdf_document_id = '${TEST_ID}' LIMIT 1;")
if [ "${NAME}" != "TEST PDF DOCUMENT DETAIL" ]; then
  echo "FAIL: expected document_name 'TEST PDF DOCUMENT DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known pdf_document_id resolves to the correct record (query mirrors 'Get PDF Document Detail': SELECT * FROM pdf_document WHERE pdf_document_id = ...)"

echo "[2/2] Unknown pdf_document_id returns zero rows (workflow maps this to statusCode 404 in 'Build PDF Document Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM pdf_document WHERE pdf_document_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent pdf_document_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent pdf_document_id resolves to zero rows at the DB level; 'Build PDF Document Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-DOCUMENT-DETAIL-001"
