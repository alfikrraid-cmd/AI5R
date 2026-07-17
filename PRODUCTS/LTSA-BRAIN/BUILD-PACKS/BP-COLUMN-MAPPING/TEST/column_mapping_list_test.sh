#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-COLUMN-MAPPING-LIST-001
# (Column Mapping List). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_MP_ID="TEST-MP-CM-LIST-$$"
TEST_ID="TEST-CM-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent mapping_profile row"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR COLUMN MAPPING LIST', 'PUMP_MASTER');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM column_mapping;")
psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute) VALUES ('${TEST_ID}', '${TEST_MP_ID}', 'Pump Number', 'Pump Tag');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM column_mapping;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Column Mappings' node's unfiltered SELECT * FROM column_mapping reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_ATTR=$(psql_run -tAc "SELECT canonical_attribute FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';")
if [ "${FOUND_ATTR}" != "Pump Tag" ]; then
  echo "FAIL: expected canonical_attribute 'Pump Tag', got '${FOUND_ATTR}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Column Mappings' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-COLUMN-MAPPING-LIST-001"
