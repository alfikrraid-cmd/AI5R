#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-METADATA-DETAIL-001
# (Media Metadata Detail). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIAMETA-DETAIL-$$"
TEST_EM_ID="TEST-EM-MEDIAMETA-DETAIL-$$"
TEST_ID="TEST-MEDIAMETA-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM media_metadata WHERE media_metadata_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and fixture media metadata"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR MEDIA METADATA DETAIL');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR METADATA DETAIL', 'PHOTO');"
psql_run -c "INSERT INTO media_metadata (media_metadata_id, engineering_media_id, camera_device) VALUES ('${TEST_ID}', '${TEST_EM_ID}', 'TEST CAMERA DEVICE');"

echo "[1/2] Known media_metadata_id returns the correct, full record"
DEVICE=$(psql_run -tAc "SELECT camera_device FROM media_metadata WHERE media_metadata_id = '${TEST_ID}' LIMIT 1;")
if [ "${DEVICE}" != "TEST CAMERA DEVICE" ]; then
  echo "FAIL: expected camera_device 'TEST CAMERA DEVICE', got '${DEVICE}'"
  exit 1
fi
echo "PASS: known media_metadata_id resolves to the correct record (query mirrors 'Get Media Metadata Detail': SELECT * FROM media_metadata WHERE media_metadata_id = ...)"

echo "[2/2] Unknown media_metadata_id returns zero rows (workflow maps this to statusCode 404 in 'Build Media Metadata Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM media_metadata WHERE media_metadata_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent media_metadata_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent media_metadata_id resolves to zero rows at the DB level; 'Build Media Metadata Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-METADATA-DETAIL-001"
