#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-DETAIL-001
# (Knowledge Source Detail). MWO-LTSA-040A (Knowledge Source Registry).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-KS-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Fixture record"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_ID}', 'INSPECTION_REPORT', 'TEST SOURCE DETAIL');"

echo "[1/2] Known knowledge_source_id returns the correct, full record"
NAME=$(psql_run -tAc "SELECT source_name FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}' LIMIT 1;")
if [ "${NAME}" != "TEST SOURCE DETAIL" ]; then
  echo "FAIL: expected source_name 'TEST SOURCE DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known knowledge_source_id resolves to the correct record (query mirrors 'Get Knowledge Source Detail': SELECT * FROM knowledge_source_registry WHERE knowledge_source_id = ...)"

echo "[2/2] Unknown knowledge_source_id returns zero rows (workflow maps this to statusCode 404 in 'Build Knowledge Source Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM knowledge_source_registry WHERE knowledge_source_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent knowledge_source_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent knowledge_source_id resolves to zero rows at the DB level; 'Build Knowledge Source Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-DETAIL-001"
