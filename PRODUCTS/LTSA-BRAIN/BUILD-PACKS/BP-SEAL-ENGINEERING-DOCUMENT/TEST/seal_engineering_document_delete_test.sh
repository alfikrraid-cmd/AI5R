#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-DELETE-001
# (Engineering Document Delete). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
#
# Uses a record created and destroyed solely within this test (not shared
# with seal_engineering_document_detail_test.sh / _update_test.sh fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-DOC-DELETE-$$"
TEST_DOC_CODE="TEST-DOC-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR DOCUMENT DELETE');"
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, document_type, title) VALUES ('${TEST_DOC_CODE}', '${TEST_SEAL_CODE}', 'INSPECTION_SHEET', 'TEST DOC DELETE');"

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal"
psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this document_code would now return 404"

echo "[2/2] Unknown document_code deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM seal_engineering_document WHERE document_code = 'DOES-NOT-EXIST-$$' RETURNING document_code;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent document_code"
  exit 1
fi
echo "PASS: nonexistent document_code affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-DELETE-001"
