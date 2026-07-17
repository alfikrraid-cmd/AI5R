#!/usr/bin/env bash
# LTSA-BRAIN Verification Runner
# MWO-P-006 / WP-002 (Verification Runner).
#
# Discovers and executes every functional test script under
# BUILD-PACKS/*/TEST/, reporting a consolidated PASS / FAIL / SKIP summary.
# Exits non-zero if any test fails, 0 otherwise (including when all tests
# are skipped or none are found to have run for a reason other than failure).
#
# Each discovered script is run as its own process and resolves its own
# database connection independently (via LTSA_TEST_DSN or standard libpq
# environment variables) -- scripts are not assumed to source
# VERIFICATION/lib/psql_common.sh, since Customer Registry's existing
# scripts do not (see MWO-P-006 WP-001 Known Risks).
#
# Scripts whose first 10 lines contain the word "DEPRECATED" are skipped,
# not run -- this respects the deprecation-marking convention already
# established across this product (SQL/shell comment headers, JSON
# metadata fields) rather than executing a known-superseded test against
# an external, unverifiable host (customer_registry_test.sh).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRODUCT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mapfile -t TEST_SCRIPTS < <(find "$PRODUCT_ROOT/BUILD-PACKS" -type f -name "*_test.sh" | sort)

if [ "${#TEST_SCRIPTS[@]}" -eq 0 ]; then
  echo "No test scripts discovered under $PRODUCT_ROOT/BUILD-PACKS/*/TEST/"
  exit 1
fi

echo "Discovered ${#TEST_SCRIPTS[@]} test script(s):"
for t in "${TEST_SCRIPTS[@]}"; do
  echo "  - ${t#$PRODUCT_ROOT/}"
done
echo ""

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
FAILED_SCRIPTS=()
SKIPPED_SCRIPTS=()

for t in "${TEST_SCRIPTS[@]}"; do
  REL_PATH="${t#$PRODUCT_ROOT/}"

  if head -n 10 "$t" | grep -qi "DEPRECATED"; then
    echo "=== SKIP (deprecated): $REL_PATH ==="
    SKIP_COUNT=$((SKIP_COUNT + 1))
    SKIPPED_SCRIPTS+=("$REL_PATH")
    echo ""
    continue
  fi

  echo "=== Running $REL_PATH ==="
  # Wrapped in `timeout` because scripts predating this MWO (e.g. Customer
  # Registry's original test scripts, not modified by this MWO) inline a
  # psql invocation without -w and can hang indefinitely on an interactive
  # password prompt when no credential is available -- discovered by actual
  # execution during WP-004, not assumed. New scripts sourcing
  # lib/psql_common.sh fail fast instead (see that file's -w fix), but the
  # runner does not assume every discovered script does.
  if timeout 60 bash "$t"; then
    echo "--- PASS: $REL_PATH ---"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    RC=$?
    if [ "$RC" -eq 124 ]; then
      echo "--- FAIL (timed out after 60s, likely blocked on an interactive prompt): $REL_PATH ---"
    else
      echo "--- FAIL: $REL_PATH ---"
    fi
    FAIL_COUNT=$((FAIL_COUNT + 1))
    FAILED_SCRIPTS+=("$REL_PATH")
  fi
  echo ""
done

echo "=== Verification Summary ==="
echo "Discovered: ${#TEST_SCRIPTS[@]}"
echo "Passed:     $PASS_COUNT"
echo "Failed:     $FAIL_COUNT"
echo "Skipped:    $SKIP_COUNT (deprecated)"

if [ "$SKIP_COUNT" -gt 0 ]; then
  echo ""
  echo "Skipped scripts:"
  for s in "${SKIPPED_SCRIPTS[@]}"; do
    echo "  - $s"
  done
fi

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo ""
  echo "Failed scripts:"
  for f in "${FAILED_SCRIPTS[@]}"; do
    echo "  - $f"
  done
  exit 1
fi

exit 0
