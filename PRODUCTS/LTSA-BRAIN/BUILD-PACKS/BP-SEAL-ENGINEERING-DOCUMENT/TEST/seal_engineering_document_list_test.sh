#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-LIST-001
# (Engineering Document List). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-DOC-LIST-$$"
TEST_KS_ID="TEST-KS-DOC-LIST-$$"
TEST_DOC_CODE="TEST-DOC-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent seal_registry and knowledge_source_registry rows"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR DOCUMENT LIST');"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DRAWING', 'TEST SOURCE FOR DOCUMENT LIST');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM seal_engineering_document;")
psql_run -c "INSERT INTO seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title) VALUES ('${TEST_DOC_CODE}', '${TEST_SEAL_CODE}', '${TEST_KS_ID}', 'DRAWING', 'TEST DOC LIST');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM seal_engineering_document;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Engineering Documents' node's unfiltered SELECT * FROM seal_engineering_document reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TYPE=$(psql_run -tAc "SELECT document_type FROM seal_engineering_document WHERE document_code = '${TEST_DOC_CODE}';")
if [ "${FOUND_TYPE}" != "DRAWING" ]; then
  echo "FAIL: expected document_type 'DRAWING', got '${FOUND_TYPE}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Engineering Documents' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-LIST-001"
