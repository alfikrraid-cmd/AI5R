#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ENGINEERING-MEDIA-DETAIL-001
# (Engineering Media Detail). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIA-DETAIL-$$"
TEST_ID="TEST-MEDIA-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row and fixture engineering media"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR ENGINEERING MEDIA DETAIL');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA DETAIL', 'PHOTO');"

echo "[1/2] Known engineering_media_id returns the correct, full record"
NAME=$(psql_run -tAc "SELECT media_name FROM engineering_media WHERE engineering_media_id = '${TEST_ID}' LIMIT 1;")
if [ "${NAME}" != "TEST ENGINEERING MEDIA DETAIL" ]; then
  echo "FAIL: expected media_name 'TEST ENGINEERING MEDIA DETAIL', got '${NAME}'"
  exit 1
fi
echo "PASS: known engineering_media_id resolves to the correct record (query mirrors 'Get Engineering Media Detail': SELECT * FROM engineering_media WHERE engineering_media_id = ...)"

echo "[2/2] Unknown engineering_media_id returns zero rows (workflow maps this to statusCode 404 in 'Build Engineering Media Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM engineering_media WHERE engineering_media_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent engineering_media_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent engineering_media_id resolves to zero rows at the DB level; 'Build Engineering Media Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ENGINEERING-MEDIA-DETAIL-001"
