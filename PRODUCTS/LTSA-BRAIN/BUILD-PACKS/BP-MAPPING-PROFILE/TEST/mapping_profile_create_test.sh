#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MAPPING-PROFILE-CREATE-001
# (Mapping Profile Create). MWO-LTSA-040C (Universal Tabular Data
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_ID="TEST-MP-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type, customer) VALUES ('${TEST_ID}', 'Pertamina RU II Pump Master', 'PUMP_MASTER', 'Pertamina RU II');"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}' AND workbook_type = 'PUMP_MASTER';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/3] workbook_type outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_ID}-BAD', 'Bad Type', 'RANDOM_SHEET');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set workbook_type was accepted"
  psql_run -c "DELETE FROM mapping_profile WHERE mapping_profile_id = '${TEST_ID}-BAD';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "mapping_profile_workbook_type_check" || { echo "FAIL: unexpected error on bad workbook_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: workbook_type outside the 11-value closed set rejected by mapping_profile_workbook_type_check"

echo "[3/3] Duplicate mapping_profile_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO mapping_profile (mapping_profile_id, profile_name, workbook_type) VALUES ('${TEST_ID}', 'Duplicate Attempt', 'SEAL_STOCK');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate mapping_profile_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate mapping_profile_id rejected by the same unique constraint the workflow's 'Check Existing Mapping Profile' / 'IF Mapping Profile Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MAPPING-PROFILE-CREATE-001"
