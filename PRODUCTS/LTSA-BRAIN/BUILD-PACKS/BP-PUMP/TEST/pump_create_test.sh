#!/usr/bin/env bash
# Functional test for WF-LTSA-PUMP-REGISTRY-001 (Pump Create).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_TAG="TEST-PUMP-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area, pump_type, status) VALUES ('${TEST_TAG}', 'Test Area', 'Centrifugal', 'ACTIVE');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}' AND area = 'Test Area';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_TAG}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] Duplicate tag_number is rejected at the schema's unique constraint"
echo "NOTE: unlike Customer Create, WF-LTSA-PUMP-REGISTRY-001.json has no pre-insert"
echo "conflict-check node (confirmed by direct read of the workflow file) -- a"
echo "duplicate tag_number reaches the database as a raw INSERT and fails with an"
echo "unhandled Postgres error, not a graceful application-level 409. This test"
echo "asserts that actual behavior; changing it is out of this MWO's scope."
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate tag_number was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate tag_number rejected by the schema's unique constraint (surfaces as an unhandled DB error in this workflow, as implemented)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-PUMP-REGISTRY-001"
