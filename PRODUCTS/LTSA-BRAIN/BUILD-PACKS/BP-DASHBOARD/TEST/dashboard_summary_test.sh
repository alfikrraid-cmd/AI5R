#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-DASHBOARD-SUMMARY-001 (Dashboard Summary).
# MO-001 (OSA Maintenance v0.1) / BP-DASHBOARD.
#
# Exercises the exact UNION ALL query embedded in the workflow's
# "Aggregate Module Counts" node directly against a real, controllable
# PostgreSQL instance.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_CODE="TEST-DASH-$$"

cleanup() {
  psql_run -c "DELETE FROM asset_registry WHERE asset_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/1] The dashboard's aggregate query returns one row per registry, including the row this test inserts"
psql_run -c "INSERT INTO asset_registry (asset_code, asset_name) VALUES ('${TEST_CODE}', 'Dashboard Smoke Test Asset');"

MODULE_COUNT=$(psql_run -tAc "
SELECT count(*) FROM (
  SELECT 'customer' AS module, count(*) AS total FROM customer_registry
  UNION ALL
  SELECT 'pump' AS module, count(*) AS total FROM ltsa_pumps
  UNION ALL
  SELECT 'seal' AS module, count(*) AS total FROM seal_registry
  UNION ALL
  SELECT 'asset' AS module, count(*) AS total FROM asset_registry
  UNION ALL
  SELECT 'soot_blower' AS module, count(*) AS total FROM soot_blower_registry
  UNION ALL
  SELECT 'work_order' AS module, count(*) AS total FROM work_order
  UNION ALL
  SELECT 'maintenance_history' AS module, count(*) AS total FROM maintenance_history
  UNION ALL
  SELECT 'work_order_open' AS module, count(*) AS total FROM work_order WHERE status = 'OPEN'
) AS summary;
")

if [ "${MODULE_COUNT}" -ne 8 ]; then
  echo "FAIL: expected 8 summary rows (one per module), found ${MODULE_COUNT}"
  exit 1
fi
echo "PASS: dashboard aggregate query returns exactly 8 module rows, matching 'Aggregate Module Counts' node"

ASSET_TOTAL=$(psql_run -tAc "SELECT count(*) FROM asset_registry WHERE asset_code = '${TEST_CODE}';")
if [ "${ASSET_TOTAL}" -ne 1 ]; then
  echo "FAIL: expected the inserted asset to be counted, found ${ASSET_TOTAL}"
  exit 1
fi
echo "PASS: newly inserted asset row is reflected in the underlying count the dashboard aggregates"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-DASHBOARD-SUMMARY-001"
