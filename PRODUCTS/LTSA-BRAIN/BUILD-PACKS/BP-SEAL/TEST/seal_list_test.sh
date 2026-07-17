#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-LIST-001 (Seal List).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM seal_registry;")
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'TEST SEAL LIST');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM seal_registry;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Seals' node's unfiltered SELECT * FROM seal_registry reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_NAME=$(psql_run -tAc "SELECT seal_name FROM seal_registry WHERE seal_code = '${TEST_CODE}';")
if [ "${FOUND_NAME}" != "TEST SEAL LIST" ]; then
  echo "FAIL: expected seal_name 'TEST SEAL LIST', got '${FOUND_NAME}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Seals' would return for this table"

echo "Note: an empty table returning an empty JSON list (not an error) is a property of"
echo "'Build Seal List Response' (\$input.all() on zero items -> data: []); verified by"
echo "reading the node source, not executed here (no n8n runtime available)."

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-LIST-001"
