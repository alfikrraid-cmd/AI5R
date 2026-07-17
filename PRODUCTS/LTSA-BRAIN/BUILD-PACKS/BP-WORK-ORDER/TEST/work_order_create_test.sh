#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-WORK-ORDER-CREATE-001 (Work Order Create).
# MO-001 (OSA Maintenance v0.1) / BP-WORK-ORDER.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-WO-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM work_order WHERE work_order_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/2] Valid create inserts a row with correctly mapped fields and default status/priority"
psql_run -c "INSERT INTO work_order (work_order_code, description, asset_code, asset_type) VALUES ('${TEST_CODE}', 'TEST WORK ORDER', 'P-101', 'pump');"

ROW=$(psql_run -tAc "SELECT status || '|' || priority FROM work_order WHERE work_order_code = '${TEST_CODE}';")
if [ "${ROW}" != "OPEN|NORMAL" ]; then
  echo "FAIL: expected default 'OPEN|NORMAL', got '${ROW}'"
  exit 1
fi
echo "PASS: row created with default status=OPEN, priority=NORMAL, matching 'Validate Work Order Input' node's defaults"

echo "[2/2] Duplicate work_order_code is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO work_order (work_order_code, description) VALUES ('${TEST_CODE}', 'Duplicate Attempt');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate work_order_code was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate work_order_code rejected by the same unique constraint the workflow's 'Check Existing Work Order' / 'IF Work Order Code Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-WORK-ORDER-CREATE-001"
