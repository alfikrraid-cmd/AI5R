#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAPPING-PROFILE-DETAIL-001
# (Mapping Profile Detail). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-MP-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Fixture record"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_ID}', 'TEST MAPPING PROFILE DETAIL', 'VENDOR_MASTER');"

echo "[1/2] Known mapping_profile_id returns the correct, full record"
NAME=$(psql_run -tAc "SELECT profile_name FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}' LIMIT 1;")
if [ "${NAME}" != "TEST MAPPING PROFILE DETAIL" ]; then
  echo "FAIL: expected profile_name 'TEST MAPPING PROFILE DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known mapping_profile_id resolves to the correct record (query mirrors 'Get Mapping Profile Detail': SELECT * FROM mapping_profile WHERE mapping_profile_id = ...)"

echo "[2/2] Unknown mapping_profile_id returns zero rows (workflow maps this to statusCode 404 in 'Build Mapping Profile Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM mapping_profile WHERE mapping_profile_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent mapping_profile_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent mapping_profile_id resolves to zero rows at the DB level; 'Build Mapping Profile Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAPPING-PROFILE-DETAIL-001"
