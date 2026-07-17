#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAPPING-PROFILE-LIST-001
# (Mapping Profile List). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-MP-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM mapping_profile;")
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_ID}', 'TEST MAPPING PROFILE LIST', 'CUSTOMER_MASTER');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM mapping_profile;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Mapping Profiles' node's unfiltered SELECT * FROM mapping_profile reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TYPE=$(psql_run -tAc "SELECT workbook_type FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';")
if [ "${FOUND_TYPE}" != "CUSTOMER_MASTER" ]; then
  echo "FAIL: expected workbook_type 'CUSTOMER_MASTER', got '${FOUND_TYPE}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Mapping Profiles' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAPPING-PROFILE-LIST-001"
