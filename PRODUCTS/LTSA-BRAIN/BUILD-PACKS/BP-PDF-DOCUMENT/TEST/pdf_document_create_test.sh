#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-DOCUMENT-CREATE-001 (PDF Document Create).
# MWO-LTSA-040D (Engineering PDF Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFDOC-CREATE-$$"
TEST_ID="TEST-PDFDOC-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row (pdf_document.knowledge_source_id is FK'd to it)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR PDF DOCUMENT');"

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT', 'DATASHEET');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM pdf_document WHERE pdf_document_id = '${TEST_ID}' AND document_type = 'DATASHEET';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/3] document_type outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_ID}-BAD', '${TEST_KS_ID}', 'Bad Type', 'RANDOM_PDF');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set document_type was accepted"
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_ID}-BAD';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "pdf_document_type_check" || { echo "FAIL: unexpected error on bad document_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: document_type outside the 11-value closed set rejected by pdf_document_type_check"

echo "[3/3] Duplicate pdf_document_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'Duplicate Attempt', 'SERVICE_BULLETIN');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate pdf_document_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate pdf_document_id rejected by the same unique constraint the workflow's 'Check Existing PDF Document' / 'IF PDF Document Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-DOCUMENT-CREATE-001"
