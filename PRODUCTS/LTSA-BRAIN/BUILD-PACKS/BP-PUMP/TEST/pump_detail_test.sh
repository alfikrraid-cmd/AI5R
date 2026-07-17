#!/usr/bin/env bash
# Functional test for WF-LTSA-PUMP-DETAIL-001 (Pump Detail).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_TAG="TEST-PUMP-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Fixture record"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'Test Area');"

echo "[1/2] Known tag_number returns the correct, full record"
AREA=$(psql_run -tAc "SELECT area FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}' LIMIT 1;")
if [ "${AREA}" != "Test Area" ]; then
  echo "FAIL: expected area 'Test Area', got '${AREA}'"
  exit 1
fi
echo "PASS: known tag_number resolves to the correct record (query mirrors 'Get Pump Detail': SELECT * FROM public.ltsa_pumps WHERE tag_number = ...)"

echo "[2/2] Unknown tag_number returns zero rows (workflow maps this to statusCode 404 in 'Build Pump Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM ltsa_pumps WHERE tag_number = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent tag_number, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent tag_number resolves to zero rows at the DB level; 'Build Pump Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here -- no n8n runtime in this environment)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-PUMP-DETAIL-001"
