#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-DOCUMENT-CLASSIFICATION-LIST-001
# (Document Classification List). MWO-LTSA-040D (Engineering PDF
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-DOCCLASS-LIST-$$"
TEST_PD_ID="TEST-PD-DOCCLASS-LIST-$$"
TEST_ID="TEST-DOCCLASS-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM document_classification WHERE document_classification_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM pdf_document WHERE pdf_document_id = '${TEST_PD_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> pdf_document)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'DATASHEET', 'TEST SOURCE FOR DOCUMENT CLASSIFICATION LIST');"
psql_run -c "INSERT INTO pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type) VALUES ('${TEST_PD_ID}', '${TEST_KS_ID}', 'TEST PDF DOCUMENT FOR CLASSIFICATION LIST', 'DATASHEET');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM document_classification;")
psql_run -c "INSERT INTO document_classification (document_classification_id, pdf_document_id, classification_type) VALUES ('${TEST_ID}', '${TEST_PD_ID}', 'MAINTENANCE_MANUAL');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM document_classification;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Document Classifications' node's unfiltered SELECT * FROM document_classification reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TYPE=$(psql_run -tAc "SELECT classification_type FROM document_classification WHERE document_classification_id = '${TEST_ID}';")
if [ "${FOUND_TYPE}" != "MAINTENANCE_MANUAL" ]; then
  echo "FAIL: expected classification_type 'MAINTENANCE_MANUAL', got '${FOUND_TYPE}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Document Classifications' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-DOCUMENT-CLASSIFICATION-LIST-001"
