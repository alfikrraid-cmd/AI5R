#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-METADATA-CREATE-001
# (Media Metadata Create). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIAMETA-CREATE-$$"
TEST_EM_ID="TEST-EM-MEDIAMETA-CREATE-$$"
TEST_ID="TEST-MEDIAMETA-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM media_metadata WHERE media_metadata_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> engineering_media)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR MEDIA METADATA');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR METADATA', 'PHOTO');"

echo "[1/2] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO media_metadata (media_metadata_id, engineering_media_id, resolution, width, height) VALUES ('${TEST_ID}', '${TEST_EM_ID}', '4K', 3840, 2160);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM media_metadata WHERE media_metadata_id = '${TEST_ID}' AND resolution = '4K';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/2] A second Media Metadata row for the same engineering_media_id is rejected (one-metadata-per-media, mirrors pdf_metadata's UNIQUE precedent)"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO media_metadata (media_metadata_id, engineering_media_id) VALUES ('${TEST_ID}-DUP', '${TEST_EM_ID}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: a second media_metadata row for the same engineering_media_id was accepted"
  psql_run -c "DELETE FROM media_metadata WHERE media_metadata_id = '${TEST_ID}-DUP';" >/dev/null 2>&1 || true
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "media_metadata_engineering_media_id_unique" || { echo "FAIL: unexpected error on duplicate engineering_media_id: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: second media_metadata row for the same engineering_media_id rejected by media_metadata_engineering_media_id_unique"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-METADATA-CREATE-001"
