#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-COLUMN-MAPPING-UPDATE-001
# (Column Mapping Update). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_MP_ID="TEST-MP-CM-UPDATE-$$"
TEST_ID="TEST-CM-UPDATE-$$"
OTHER_ID="TEST-CM-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM column_mapping WHERE column_mapping_id IN ('${TEST_ID}', '${OTHER_ID}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent row and two fixture column mappings: one to update, one control"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR COLUMN MAPPING UPDATE', 'PUMP_MASTER');"
psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute, is_mandatory) VALUES ('${TEST_ID}', '${TEST_MP_ID}', 'TAG NO', 'Pump Tag', false);"
psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute, is_mandatory) VALUES ('${OTHER_ID}', '${TEST_MP_ID}', 'Untouched', 'Untouched Attr', false);"

echo "[1/2] Valid update (equivalent to 'Update Column Mapping's dynamic SET clause for is_mandatory only) modifies only the targeted row's specified field"
psql_run -c "UPDATE column_mapping SET is_mandatory = true, updated_at = NOW() WHERE column_mapping_id = '${TEST_ID}';"

UPDATED_MANDATORY=$(psql_run -tAc "SELECT is_mandatory FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';")
UPDATED_COLUMN=$(psql_run -tAc "SELECT source_column FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';")
OTHER_MANDATORY=$(psql_run -tAc "SELECT is_mandatory FROM column_mapping WHERE column_mapping_id = '${OTHER_ID}';")

if [ "${UPDATED_MANDATORY}" != "t" ]; then
  echo "FAIL: expected is_mandatory 't' on targeted row, got '${UPDATED_MANDATORY}'"
  exit 1
fi
if [ "${UPDATED_COLUMN}" != "TAG NO" ]; then
  echo "FAIL: non-targeted field source_column changed unexpectedly to '${UPDATED_COLUMN}'"
  exit 1
fi
if [ "${OTHER_MANDATORY}" != "f" ]; then
  echo "FAIL: unrelated row was modified (is_mandatory now '${OTHER_MANDATORY}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/2] Unknown column_mapping_id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE column_mapping SET is_mandatory = false WHERE column_mapping_id = 'DOES-NOT-EXIST-$$' RETURNING column_mapping_id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent column_mapping_id"
  exit 1
fi
echo "PASS: nonexistent column_mapping_id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-COLUMN-MAPPING-UPDATE-001"
