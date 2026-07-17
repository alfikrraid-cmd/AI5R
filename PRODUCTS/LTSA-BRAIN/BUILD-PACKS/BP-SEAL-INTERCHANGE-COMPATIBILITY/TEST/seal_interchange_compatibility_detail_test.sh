#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-DETAIL-001
# (Interchange Compatibility Detail). MWO-LTSA-030 (Mechanical Seal Knowledge
# Manufacturing).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_SEAL_A="TEST-SEAL-IC-DETAIL-A-$$"
TEST_SEAL_B="TEST-SEAL-IC-DETAIL-B-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM seal_registry WHERE seal_code IN ('${TEST_SEAL_A}', '${TEST_SEAL_B}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two parent rows and a fixture interchange record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_SEAL_A}', 'TEST SEAL A'), ('${TEST_SEAL_B}', 'TEST SEAL B');"
psql_run -c "INSERT INTO seal_interchange_compatibility (seal_code, compatible_seal_code, notes) VALUES ('${TEST_SEAL_A}', '${TEST_SEAL_B}', 'DETAIL NOTE');"

echo "[1/2] Known (seal_code, compatible_seal_code) pair returns the correct, full record"
NOTES=$(psql_run -tAc "SELECT notes FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = '${TEST_SEAL_B}' LIMIT 1;")
if [ "${NOTES}" != "DETAIL NOTE" ]; then
  echo "FAIL: expected notes 'DETAIL NOTE', got '${NOTES}'"
  exit 1
fi
echo "PASS: known composite key resolves to the correct record (query mirrors 'Get Interchange Compatibility Detail': SELECT * FROM seal_interchange_compatibility WHERE seal_code = ... AND compatible_seal_code = ...)"

echo "[2/2] Unknown composite key returns zero rows (workflow maps this to statusCode 404 in 'Build Interchange Compatibility Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_interchange_compatibility WHERE seal_code = '${TEST_SEAL_A}' AND compatible_seal_code = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent compatible_seal_code, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent composite key resolves to zero rows at the DB level; 'Build Interchange Compatibility Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-INTERCHANGE-COMPATIBILITY-DETAIL-001"
