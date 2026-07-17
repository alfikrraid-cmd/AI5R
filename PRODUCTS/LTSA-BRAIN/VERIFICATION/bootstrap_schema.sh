#!/usr/bin/env bash
# Applies the LTSA-BRAIN canonical schema to the target database, idempotently.
# MWO-P-006 / WP-001 (Verification Framework).
#
# Requires LTSA_TEST_DSN or standard libpq environment variables to be set
# by the caller. Safe to run repeatedly: every statement in
# DATABASE/CANONICAL_SCHEMA.sql uses CREATE EXTENSION IF NOT EXISTS,
# CREATE TABLE IF NOT EXISTS, and CREATE INDEX IF NOT EXISTS (confirmed by
# direct read before writing this script) -- running it against a database
# that already has the schema applied is a no-op, not an error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/../DATABASE/CANONICAL_SCHEMA.sql"

# shellcheck source=lib/psql_common.sh
source "$SCRIPT_DIR/lib/psql_common.sh"

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "FAIL: canonical schema file not found at $SCHEMA_FILE"
  exit 1
fi

echo "Applying canonical schema from $SCHEMA_FILE ..."
if [ -n "$DSN" ]; then
  psql "$DSN" -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE"
else
  psql -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE"
fi
echo "Canonical schema applied (customer_registry, ltsa_pumps, seal_registry)."
