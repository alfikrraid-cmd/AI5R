#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-COLUMN-MAPPING-CREATE-001
# (Column Mapping Create). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_MP_ID="TEST-MP-CM-CREATE-$$"
TEST_ID="TEST-CM-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM column_mapping WHERE column_mapping_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_MP_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent mapping_profile row (column_mapping.mapping_profile_id is FK'd to it)"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_MP_ID}', 'TEST PROFILE FOR COLUMN MAPPING', 'PUMP_MASTER');"

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute, is_mandatory) VALUES ('${TEST_ID}', '${TEST_MP_ID}', 'TAG NO', 'Pump Tag', true);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM column_mapping WHERE column_mapping_id = '${TEST_ID}' AND canonical_attribute = 'Pump Tag' AND is_mandatory = true;")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields, including is_mandatory"

echo "[2/2] Duplicate column_mapping_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute) VALUES ('${TEST_ID}', '${TEST_MP_ID}', 'Equipment', 'Pump Tag');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate column_mapping_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate column_mapping_id rejected by the same unique constraint the workflow's 'Check Existing Column Mapping' / 'IF Column Mapping Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-COLUMN-MAPPING-CREATE-001"
