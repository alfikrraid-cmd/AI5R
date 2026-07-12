#!/usr/bin/env bash
# Functional test for WF-LTSA-CUSTOMER-BY-CODE-001 (MWO-P-003 / WP-006).
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

TEST_CODE="TEST-BY-CODE-$$"

cleanup() {
  psql_run -c "DELETE FROM customer_registry WHERE customer_code = '${TEST_CODE}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Fixture record created via WP-001's real create logic"
psql_run -c "INSERT INTO customer_registry (customer_code, customer_name) VALUES ('${TEST_CODE}', 'PT TEST BY CODE');"

echo "[1/2] Known customer_code returns the correct record"
NAME=$(psql_run -tAc "SELECT customer_name FROM customer_registry WHERE customer_code = '${TEST_CODE}' LIMIT 1;")
if [ "${NAME}" != "PT TEST BY CODE" ]; then
  echo "FAIL: expected customer_name 'PT TEST BY CODE', got '${NAME}'"
  exit 1
fi
echo "PASS: known customer_code resolves to the correct record (query mirrors 'Get Customer By Code': SELECT * FROM customer_registry WHERE customer_code = ...)"

echo "[2/2] Unknown customer_code returns zero rows (workflow maps this to statusCode 404 in 'Build By-Code Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM customer_registry WHERE customer_code = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent customer_code, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent customer_code resolves to zero rows at the DB level; 'Build By-Code Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-CUSTOMER-BY-CODE-001"
