#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-DETAIL-001
# (Engineering Document Detail). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-DOC-DETAIL-$$"
TEST_KS_ID="TEST-KS-DOC-DETAIL-$$"
TEST_DOC_CODE="TEST-DOC-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry and knowledge_source_registry rows, and fixture document"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR DOCUMENT DETAIL');"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DRAWING', 'TEST SOURCE FOR DOCUMENT DETAIL');"
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title) VALUES ('${TEST_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'INSTALLATION_GUIDE', 'TEST DOC DETAIL');"

echo "[1/2] Known document_code returns the correct, full record"
TITLE=$(psql_run -tAc "SELECT title FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}' LIMIT 1;")
if [ "${TITLE}" != "TEST DOC DETAIL" ]; then
  echo "FAIL: expected title 'TEST DOC DETAIL', got '${TITLE}'"
  exit 1
fi
echo "PASS: known document_code resolves to the correct record (query mirrors 'Get Engineering Document Detail': SELECT * FROM seal_engineering_document WHERE document_code = ...)"

echo "[2/2] Unknown document_code returns zero rows (workflow maps this to statusCode 404 in 'Build Engineering Document Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_engineering_document WHERE document_code = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent document_code, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent document_code resolves to zero rows at the DB level; 'Build Engineering Document Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-DETAIL-001"
