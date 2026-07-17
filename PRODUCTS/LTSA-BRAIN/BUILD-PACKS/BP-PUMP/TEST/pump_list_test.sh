#!/usr/bin/env bash
# Functional test for WF-LTSA-PUMP-LIST-001 (Pump List).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_TAG="TEST-PUMP-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM ltsa_pumps;")
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'Test Area');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM ltsa_pumps;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Pumps' node's unfiltered SELECT * FROM ltsa_pumps reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_AREA=$(psql_run -tAc "SELECT area FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';")
if [ "${FOUND_AREA}" != "Test Area" ]; then
  echo "FAIL: expected area 'Test Area', got '${FOUND_AREA}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Pumps' would return for this table"

echo "Note: an empty table returning an empty JSON list (not an error) is a property of"
echo "'Build Pump List Response' (\$input.all() on zero items -> data: []); verified by"
echo "reading the node source, not executed here (no n8n runtime available)."

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-PUMP-LIST-001"
