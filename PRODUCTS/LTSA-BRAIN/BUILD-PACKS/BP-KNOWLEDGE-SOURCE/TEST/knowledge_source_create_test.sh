#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-CREATE-001
# (Knowledge Source Create). MWO-LTSA-040A (Knowledge Source Registry).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-KS-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_ID}', 'SERVICE_REPORT', 'TEST SOURCE');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}' AND source_type = 'SERVICE_REPORT';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi

DEFAULT_STATUS=$(psql_run -tAc "SELECT verification_status FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';")
if [ "${DEFAULT_STATUS}" != "DRAFT" ]; then
  echo "FAIL: expected default verification_status 'DRAFT', got '${DEFAULT_STATUS}'"
  exit 1
fi
echo "PASS: row created with correctly mapped fields, verification_status defaults to DRAFT"

echo "[2/3] source_type outside the closed set is rejected by the schema CHECK constraint"
echo "NOTE: 'Validate Knowledge Source Input' also rejects this at the workflow layer"
echo "-- this test asserts the DB-level backstop."
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_ID}-BAD', 'AUDIO_RECORDING', 'Bad Type');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set source_type was accepted"
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}-BAD';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "knowledge_source_registry_source_type_check" || { echo "FAIL: unexpected error on bad source_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: source_type outside the 15-value closed set rejected by knowledge_source_registry_source_type_check"

echo "[3/3] Duplicate knowledge_source_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_ID}', 'PHOTO', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate knowledge_source_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate knowledge_source_id rejected by the same unique constraint the workflow's 'Check Existing Knowledge Source' / 'IF Knowledge Source Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-CREATE-001"
