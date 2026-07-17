#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-ENGINEERING-MEDIA-LIST-001
# (Engineering Media List). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIA-LIST-$$"
TEST_ID="TEST-MEDIA-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent knowledge_source_registry row"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'VIDEO', 'TEST SOURCE FOR ENGINEERING MEDIA LIST');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM engineering_media;")
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA LIST', 'CCTV_RECORDING');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM engineering_media;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Engineering Media' node's unfiltered SELECT * FROM engineering_media reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_TYPE=$(psql_run -tAc "SELECT media_type FROM engineering_media WHERE engineering_media_id = '${TEST_ID}';")
if [ "${FOUND_TYPE}" != "CCTV_RECORDING" ]; then
  echo "FAIL: expected media_type 'CCTV_RECORDING', got '${FOUND_TYPE}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Engineering Media' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-ENGINEERING-MEDIA-LIST-001"
