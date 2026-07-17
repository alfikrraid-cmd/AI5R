#!/usr/bin/env bash
# Shared PostgreSQL connection helper for LTSA-BRAIN verification scripts.
# MWO-P-006 / WP-001 (Verification Framework).
#
# Extracted, not redesigned, from the connection-resolution pattern already
# proven six times in BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/TEST/customer_*_test.sh
# (MWO-P-003). Behaviorally identical to that inline pattern.
#
# Usage: source this file, then call psql_run with any psql arguments.
# Connection is resolved via LTSA_TEST_DSN if set, otherwise falls back to
# standard libpq environment variables (PGHOST, PGPORT, PGUSER, PGPASSWORD,
# PGDATABASE) already configured in the calling environment.
#
# Customer Registry's existing test scripts each inline this same logic
# independently and are not modified to source this file (MWO-P-006 WP-001
# Known Risk) -- this library is consumed only by the new Pump and Seal
# verification scripts (WP-003) and by bootstrap_schema.sh.
#
# Correction made during WP-004 execution: the original inline pattern (and
# this file's first draft) omitted psql's -w flag. Without it, a missing
# credential does not fail fast -- psql falls back to an interactive
# password prompt that can never be satisfied in a non-interactive session,
# hanging indefinitely rather than erroring. This was discovered by actually
# attempting execution (RV-004-Verification-Report.md), not assumed, and is
# fixed here since psql_common.sh is this MWO's own new file, not a
# modification to Customer Registry's existing scripts.

DSN="${LTSA_TEST_DSN:-}"

psql_run() {
  if [ -n "$DSN" ]; then
    psql "$DSN" -w -v ON_ERROR_STOP=1 "$@"
  else
    psql -w -v ON_ERROR_STOP=1 "$@"
  fi
}
