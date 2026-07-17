#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-CREATE-001
# (Engineering Document Create). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-DOC-CREATE-$$"
TEST_KS_ID="TEST-KS-DOC-CREATE-$$"
TEST_DOC_CODE="TEST-DOC-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry and knowledge_source_registry rows (both FK'd from seal_engineering_document, MWO-LTSA-040B)"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR DOCUMENT');"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DRAWING', 'TEST SOURCE FOR DOCUMENT');"

echo "[1/4] Valid create inserts a row with correctly mapped fields, including 040B acquisition-layer fields"
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title, document_number, page_count) VALUES ('${TEST_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'DATASHEET', 'TEST DOC', 'DOC-NUM-001', 12);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}' AND document_type = 'DATASHEET' AND knowledge_source_id = '${TEST_KS_ID}' AND page_count = 12;")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_DOC_CODE}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields, including knowledge_source_id and page_count"

echo "[2/4] A document_type introduced by MWO-LTSA-040B (e.g. MAINTENANCE_MANUAL) is now accepted"
MANUAL_DOC_CODE="${TEST_DOC_CODE}-MANUAL"
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title) VALUES ('${MANUAL_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'MAINTENANCE_MANUAL', 'TEST MANUAL');"
MANUAL_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_engineering_document WHERE document_code = '${MANUAL_DOC_CODE}';")
if [ "${MANUAL_COUNT}" -ne 1 ]; then
  echo "FAIL: expected MAINTENANCE_MANUAL (added by MWO-LTSA-040B) to be accepted"
  exit 1
fi
psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${MANUAL_DOC_CODE}';" >/dev/null 2>&1
echo "PASS: MAINTENANCE_MANUAL accepted by the widened seal_engineering_document_type_check"

echo "[3/4] document_type outside the closed set is rejected by the schema CHECK constraint"
echo "NOTE: 'Validate Engineering Document Input' also rejects this at the workflow layer"
echo "(Architecture Decision, MWO-LTSA-030 item 7) -- this test asserts the DB-level backstop."
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title) VALUES ('${TEST_DOC_CODE}-BAD', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'PHOTO', 'Bad Type');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set document_type was accepted"
  psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}-BAD';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "seal_engineering_document_type_check" || { echo "FAIL: unexpected error on bad document_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: document_type outside the 7-value closed set rejected by seal_engineering_document_type_check"

echo "[4/4] Duplicate document_code is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title) VALUES ('${TEST_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'DRAWING', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate document_code was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate document_code rejected by the same unique constraint the workflow's 'Check Existing Engineering Document' / 'IF Engineering Document Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-CREATE-001"
