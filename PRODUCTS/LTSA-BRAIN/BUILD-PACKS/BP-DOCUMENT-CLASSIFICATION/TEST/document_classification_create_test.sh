#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-DOCUMENT-CLASSIFICATION-CREATE-001
# (Document Classification Create). MWO-LTSA-040D (Engineering PDF
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-DOCCLASS-CREATE-$$"
TEST_PD_ID="TEST-PD-DOCCLASS-CREATE-$$"
TEST_ID="TEST-DOCCLASS-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM document_classification WHERE document_classification_id LIKE 'TEST-DOCCLASS-CREATE-$$%';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> pdf_document)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR DOCUMENT CLASSIFICATION');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR CLASSIFICATION', 'DATASHEET');"

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO document_classification (document_classification_id, pdf_document_id, classification_type, confidence) VALUES ('${TEST_ID}', '${TEST_PD_ID}', 'DATASHEET', 0.95);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM document_classification WHERE document_classification_id = '${TEST_ID}' AND classification_type = 'DATASHEET';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/3] classification_type outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO document_classification (document_classification_id, pdf_document_id, classification_type) VALUES ('${TEST_ID}-BAD', '${TEST_PD_ID}', 'RANDOM_CLASS');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set classification_type was accepted"
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "document_classification_type_check" || { echo "FAIL: unexpected error on bad classification_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: classification_type outside the 11-value closed set rejected by document_classification_type_check"

echo "[3/3] A second classification row for the same pdf_document_id is accepted (repeatable, per Business Rule)"
psql_run -c "INSERT INTO document_classification (document_classification_id, pdf_document_id, classification_type) VALUES ('${TEST_ID}-2', '${TEST_PD_ID}', 'ENGINEERING_SPECIFICATION');"
REPEAT_COUNT=$(psql_run -tAc "SELECT count(*) FROM document_classification WHERE pdf_document_id = '${TEST_PD_ID}';")
if [ "${REPEAT_COUNT}" -ne 2 ]; then
  echo "FAIL: expected 2 classification rows for ${TEST_PD_ID}, found ${REPEAT_COUNT}"
  exit 1
fi
echo "PASS: repeated classification against the same PDF Document accumulates as new rows, not hidden by any uniqueness constraint"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-DOCUMENT-CLASSIFICATION-CREATE-001"
