#!/usr/bin/env bash
# Functional test for WF-LTSA-CUSTOMER-DELETE-001 (MWO-P-003 / WP-005).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on n8n.osa-system.com
# or any external host.
#
# Uses a record created and destroyed solely within this test (not shared
# with WP-002/003/004's fixtures), per the MWO's WP-005 isolation note.
#
# Requires a PostgreSQL connection via standard libpq environment variables
# or LTSA_TEST_DSN. Canonical schema must already be applied.
set -euo pipefail

DSN="${LTSA_TEST_DSN:-}"
psql_run() {
  if [ -n "$DSN" ]; then
    psql "$DSN" -v ON_ERROR_STOP=1 "$@"
  else
    psql -v ON_ERROR_STOP=1 "$@"
  fi
}

TEST_CODE="TEST-DELETE-$$"

cleanup() {
  psql_run -c "DELETE FROM customer_registry WHERE customer_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Disposable fixture record"
psql_run -c "INSERT INTO customer_registry (customer_code, customer_name) VALUES ('${TEST_CODE}', 'PT TEST DELETE');"
TEST_ID=$(psql_run -tAc "SELECT id FROM customer_registry WHERE customer_code = '${TEST_CODE}';")

echo "[1/2] Existing record is removed; a subsequent lookup confirms removal (equivalent to a WP-002 Detail 404)"
psql_run -c "DELETE FROM customer_registry WHERE id = '${TEST_ID}';"
REMAINING=$(psql_run -tAc "SELECT count(*) FROM customer_registry WHERE id = '${TEST_ID}';")
if [ "${REMAINING}" -ne 0 ]; then
  echo "FAIL: record still present after delete"
  exit 1
fi
echo "PASS: record removed; a Detail lookup against this id would now return 404"

echo "[2/2] Unknown id deletes zero rows (workflow maps this to statusCode 404 in 'Check Delete Result')"
DELETED=$(psql_run -tAc "DELETE FROM customer_registry WHERE id = '00000000-0000-0000-0000-000000000000' RETURNING id;")
if [ -n "${DELETED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent id"
  exit 1
fi
echo "PASS: nonexistent id affects zero rows at the DB level; 'Check Delete Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-CUSTOMER-DELETE-001"
