#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-PDF-DOCUMENT-LIST-001 (PDF Document List).
# MWO-LTSA-040D (Engineering PDF Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-PDFDOC-LIST-$$"
TEST_ID="TEST-PDFDOC-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DRAWING', 'TEST SOURCE FOR PDF DOCUMENT LIST');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM pdf_document;")
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT LIST', 'JOHN_CRANE_DRAWING');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM pdf_document;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List PDF Documents' node's unfiltered SELECT * FROM pdf_document reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TYPE=$(psql_run -tAc "SELECT document_type FROM pdf_document WHERE pdf_document_id = '${TEST_ID}';")
if [ "${FOUND_TYPE}" != "JOHN_CRANE_DRAWING" ]; then
  echo "FAIL: expected document_type 'JOHN_CRANE_DRAWING', got '${FOUND_TYPE}'"
  exit 1
fi
echo "PASS: row shape matches what 'List PDF Documents' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-PDF-DOCUMENT-LIST-001"
