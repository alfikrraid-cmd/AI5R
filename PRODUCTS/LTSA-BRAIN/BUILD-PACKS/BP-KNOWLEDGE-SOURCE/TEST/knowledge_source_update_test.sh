#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-UPDATE-001
# (Knowledge Source Update). MWO-LTSA-040A (Knowledge Source Registry).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-KS-UPDATE-$$"
OTHER_ID="TEST-KS-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id IN ('${TEST_ID}', '${OTHER_ID}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two fixture records: one to update, one control (must stay unaffected)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name, verification_status) VALUES ('${TEST_ID}', 'FAILURE_REPORT', 'Before Update', 'DRAFT');"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name, verification_status) VALUES ('${OTHER_ID}', 'FAILURE_REPORT', 'Untouched', 'DRAFT');"

echo "[1/3] Valid update (equivalent to 'Update Knowledge Source's dynamic SET clause for verification_status only) modifies only the targeted row's specified field"
psql_run -c "UPDATE knowledge_source_registry SET verification_status = 'VERIFIED', updated_at = NOW() WHERE knowledge_source_id = '${TEST_ID}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT verification_status FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';")
UPDATED_NAME=$(psql_run -tAc "SELECT source_name FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';")
OTHER_STATUS=$(psql_run -tAc "SELECT verification_status FROM knowledge_source_registry WHERE knowledge_source_id = '${OTHER_ID}';")

if [ "${UPDATED_STATUS}" != "VERIFIED" ]; then
  echo "FAIL: expected verification_status 'VERIFIED' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_NAME}" != "Before Update" ]; then
  echo "FAIL: non-targeted field source_name changed unexpectedly to '${UPDATED_NAME}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "DRAFT" ]; then
  echo "FAIL: unrelated row was modified (verification_status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/3] verification_status outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_STATUS_OUTPUT=$(psql_run -c "UPDATE knowledge_source_registry SET verification_status = 'ARCHIVED' WHERE knowledge_source_id = '${TEST_ID}';" 2>&1)
BAD_STATUS_EXIT=$?
set -e
if [ "${BAD_STATUS_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set verification_status was accepted"
  exit 1
fi
echo "${BAD_STATUS_OUTPUT}" | grep -qi "knowledge_source_registry_verification_status_check" || { echo "FAIL: unexpected error on bad verification_status: ${BAD_STATUS_OUTPUT}"; exit 1; }
echo "PASS: verification_status outside DRAFT/UNDER_REVIEW/VERIFIED/CANONICAL rejected by knowledge_source_registry_verification_status_check"

echo "[3/3] Unknown knowledge_source_id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE knowledge_source_registry SET verification_status = 'UNDER_REVIEW' WHERE knowledge_source_id = 'DOES-NOT-EXIST-$$' RETURNING knowledge_source_id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent knowledge_source_id"
  exit 1
fi
echo "PASS: nonexistent knowledge_source_id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-UPDATE-001"
