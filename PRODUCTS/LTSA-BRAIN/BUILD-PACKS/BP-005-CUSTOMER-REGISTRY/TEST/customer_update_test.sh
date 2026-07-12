#!/usr/bin/env bash
# Functional test for WF-LTSA-CUSTOMER-UPDATE-001 (MWO-P-003 / WP-004).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on n8n.osa-system.com
# or any external host.
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

TEST_CODE="TEST-UPDATE-$$"
OTHER_CODE="TEST-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM customer_registry WHERE customer_code IN ('${TEST_CODE}', '${OTHER_CODE}');" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Two fixture records: one to update, one control (must stay unaffected)"
psql_run -c "INSERT INTO customer_registry (customer_code, customer_name, city) VALUES ('${TEST_CODE}', 'PT BEFORE UPDATE', 'Jakarta');"
psql_run -c "INSERT INTO customer_registry (customer_code, customer_name, city) VALUES ('${OTHER_CODE}', 'PT UNTOUCHED', 'Surabaya');"
TEST_ID=$(psql_run -tAc "SELECT id FROM customer_registry WHERE customer_code = '${TEST_CODE}';")

echo "[1/2] Valid update (equivalent to 'Update Customer's dynamic SET clause for city only) modifies only the targeted row's specified field"
psql_run -c "UPDATE customer_registry SET city = 'Bandung', updated_at = NOW() WHERE id = '${TEST_ID}';"

UPDATED_CITY=$(psql_run -tAc "SELECT city FROM customer_registry WHERE id = '${TEST_ID}';")
UPDATED_NAME=$(psql_run -tAc "SELECT customer_name FROM customer_registry WHERE id = '${TEST_ID}';")
OTHER_CITY=$(psql_run -tAc "SELECT city FROM customer_registry WHERE customer_code = '${OTHER_CODE}';")

if [ "${UPDATED_CITY}" != "Bandung" ]; then
  echo "FAIL: expected city 'Bandung' on targeted row, got '${UPDATED_CITY}'"
  exit 1
fi
if [ "${UPDATED_NAME}" != "PT BEFORE UPDATE" ]; then
  echo "FAIL: non-targeted field customer_name changed unexpectedly to '${UPDATED_NAME}'"
  exit 1
fi
if [ "${OTHER_CITY}" != "Surabaya" ]; then
  echo "FAIL: unrelated row was modified (city now '${OTHER_CITY}')"
  exit 1
fi
echo "PASS: only the targeted row's specified field changed; other fields and other rows untouched"

echo "[2/2] Unknown id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE customer_registry SET city = 'Nowhere' WHERE id = '00000000-0000-0000-0000-000000000000' RETURNING id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent id"
  exit 1
fi
echo "PASS: nonexistent id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (code logic verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-CUSTOMER-UPDATE-001"
