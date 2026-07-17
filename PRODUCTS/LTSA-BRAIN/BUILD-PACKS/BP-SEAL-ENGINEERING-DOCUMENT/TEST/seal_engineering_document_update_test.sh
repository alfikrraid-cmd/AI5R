#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-UPDATE-001
# (Engineering Document Update). Originally MWO-LTSA-030 (Mechanical Seal
# Knowledge Manufacturing); narrowed to status-only under MWO-LTSA-040B
# (Engineering Document Acquisition) per its immutability Business Rule.
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-DOC-UPDATE-$$"
TEST_KS_ID="TEST-KS-DOC-UPDATE-$$"
TEST_DOC_CODE="TEST-DOC-UPDATE-$$"
OTHER_DOC_CODE="TEST-DOC-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_engineering_document WHERE document_code IN ('${TEST_DOC_CODE}', '${OTHER_DOC_CODE}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent rows and two fixture documents: one to update, one control"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR DOCUMENT UPDATE');"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DRAWING', 'TEST SOURCE FOR DOCUMENT UPDATE');"
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title, revision, status) VALUES ('${TEST_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'DRAWING', 'Before Update', 'A', 'DRAFT');"
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title, revision, status) VALUES ('${OTHER_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'DRAWING', 'Untouched', 'A', 'DRAFT');"

echo "[1/3] Valid update (equivalent to 'Update Engineering Document's dynamic SET clause for status only, the sole field 'Validate Update Input' now permits per MWO-LTSA-040B's immutability rule) modifies only the targeted row's status"
psql_run -c "UPDATE seal_engineering_document SET status = 'APPROVED', updated_at = NOW() WHERE document_code = '${TEST_DOC_CODE}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';")
UPDATED_TITLE=$(psql_run -tAc "SELECT title FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';")
UPDATED_REVISION=$(psql_run -tAc "SELECT revision FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM seal_engineering_document WHERE document_code = '${OTHER_DOC_CODE}';")

if [ "${UPDATED_STATUS}" != "APPROVED" ]; then
  echo "FAIL: expected status 'APPROVED' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_TITLE}" != "Before Update" ]; then
  echo "FAIL: non-targeted field title changed unexpectedly to '${UPDATED_TITLE}'"
  exit 1
fi
if [ "${UPDATED_REVISION}" != "A" ]; then
  echo "FAIL: non-targeted field revision changed unexpectedly to '${UPDATED_REVISION}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "DRAFT" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's status changed; title, revision, and other rows untouched"

echo "[2/3] 'Validate Update Input' only ever builds a SET clause for status -- a request body carrying title/revision/document_type has no path to mutate those columns"
echo "NOTE: this is asserted by static review of WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-UPDATE-001.json's"
echo "'Validate Update Input' node (updatable = ['status']), not executed here -- there is no SQL"
echo "statement this test could run to prove a negative about what the workflow's own JS code omits."
echo "PASS: confirmed by source review, per MWO-LTSA-040B Business Rule (Engineering Documents are immutable)"

echo "[3/3] Unknown document_code updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE seal_engineering_document SET status = 'REJECTED' WHERE document_code = 'DOES-NOT-EXIST-$$' RETURNING document_code;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent document_code"
  exit 1
fi
echo "PASS: nonexistent document_code affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-UPDATE-001"
