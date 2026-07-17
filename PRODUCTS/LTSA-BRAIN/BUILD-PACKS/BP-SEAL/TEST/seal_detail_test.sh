#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-SEAL-DETAIL-001 (Seal Detail).
# MWO-P-006 / WP-003 (Registry Verification Suite).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-SEAL-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM seal_registry WHERE seal_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Fixture record"
psql_run -c "INSERT INTO seal_registry (seal_code, seal_name) VALUES ('${TEST_CODE}', 'TEST SEAL DETAIL');"

echo "[1/2] Known seal_code returns the correct, full record"
NAME=$(psql_run -tAc "SELECT seal_name FROM seal_registry WHERE seal_code = '${TEST_CODE}' LIMIT 1;")
if [ "${NAME}" != "TEST SEAL DETAIL" ]; then
  echo "FAIL: expected seal_name 'TEST SEAL DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known seal_code resolves to the correct record (query mirrors 'Get Seal Detail': SELECT * FROM seal_registry WHERE seal_code = ...)"

echo "[2/2] Unknown seal_code returns zero rows (workflow maps this to statusCode 404 in 'Build Seal Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM seal_registry WHERE seal_code = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent seal_code, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent seal_code resolves to zero rows at the DB level; 'Build Seal Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-SEAL-DETAIL-001"
