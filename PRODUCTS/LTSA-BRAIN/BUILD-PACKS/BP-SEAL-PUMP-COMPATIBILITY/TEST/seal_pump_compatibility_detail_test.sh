#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-DETAIL-001
# (Pump Compatibility Detail). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_CODE="TEST-SEAL-PC-DETAIL-$$"
TEST_TAG="TEST-PUMP-PC-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_SEAL_CODE}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM ltsa_pumps WHERE tag_number = '${TEST_TAG}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent rows and fixture compatibility record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_CODE}', 'TEST SEAL FOR PUMP COMPATIBILITY DETAIL');"
psql_run -c "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('${TEST_TAG}', 'TEST-AREA');"
psql_run -c "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number, notes) VALUES ('${TEST_SEAL_CODE}', '${TEST_TAG}', 'DETAIL NOTE');"

echo "[1/2] Known (seal_code, pump_tag_number) pair returns the correct, full record"
NOTES=$(psql_run -tAc "SELECT notes FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = '${TEST_TAG}' LIMIT 1;")
if [ "${NOTES}" != "DETAIL NOTE" ]; then
  echo "FAIL: expected notes 'DETAIL NOTE', got '${NOTES}'"
  exit 1
fi
echo "PASS: known composite key resolves to the correct record (query mirrors 'Get Pump Compatibility Detail': SELECT * FROM seal_pump_compatibility WHERE seal_code = ... AND pump_tag_number = ...)"

echo "[2/2] Unknown composite key returns zero rows (workflow maps this to statusCode 404 in 'Build Pump Compatibility Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_pump_compatibility WHERE seal_code = '${TEST_SEAL_CODE}' AND pump_tag_number = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent pump_tag_number, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent composite key resolves to zero rows at the DB level; 'Build Pump Compatibility Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-DETAIL-001"
