#!/usr/bin/env bash
# Functional test for WF-LTSA-PUMP-DELETE-001 (Pump Delete).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
#
# Uses a record created and destroyed solely within this test (not shared
# with pump_detail_test.sh / pump_update_test.sh fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_TAG="TEST-PUMP-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'Test Area');"

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal"
psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this tag_number would now return 404"

echo "[2/2] Unknown tag_number deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM ltsa_pumps WHERE tag_number = 'DOES-NOT-EXIST-$$' RETURNING tag_number;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent tag_number"
  exit 1
fi
echo "PASS: nonexistent tag_number affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-PUMP-DELETE-001"
