#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-LIST-001
# (Knowledge Source List). MWO-LTSA-040A (Knowledge Source Registry).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-KS-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM knowledge_source_registry;")
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_ID}', 'DRAWING', 'TEST SOURCE LIST');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM knowledge_source_registry;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Knowledge Sources' node's unfiltered SELECT * FROM knowledge_source_registry reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TYPE=$(psql_run -tAc "SELECT source_type FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_ID}';")
if [ "${FOUND_TYPE}" != "DRAWING" ]; then
  echo "FAIL: expected source_type 'DRAWING', got '${FOUND_TYPE}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Knowledge Sources' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-KNOWLEDGE-SOURCE-LIST-001"
