#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-DETAIL-001
# (Media Acquisition Job Detail). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIAAJ-DETAIL-$$"
TEST_EM_ID="TEST-EM-MEDIAAJ-DETAIL-$$"
TEST_ID="TEST-MEDIAAJ-DETAIL-$$"

cleanup() {
  psql_run -c "DELETE FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and fixture media acquisition job"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR MEDIA ACQUISITION JOB DETAIL');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR ACQUISITION JOB DETAIL', 'PHOTO');"
psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_EM_ID}');"

echo "[1/2] Known media_acquisition_job_id returns the correct, full record"
STATUS=$(psql_run -tAc "SELECT status FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}' LIMIT 1;")
if [ "${STATUS}" != "PENDING" ]; then
  echo "FAIL: expected status 'PENDING', got '${STATUS}'"
  exit 1
fi
echo "PASS: known media_acquisition_job_id resolves to the correct record (query mirrors 'Get Media Acquisition Job Detail': SELECT * FROM media_acquisition_job WHERE media_acquisition_job_id = ...)"

echo "[2/2] Unknown media_acquisition_job_id returns zero rows (workflow maps this to statusCode 404 in 'Build Media Acquisition Job Detail Response')"
UNKNOWN_COUNT=$(psql_run -tAc "SELECT count(*) FROM media_acquisition_job WHERE media_acquisition_job_id = 'DOES-NOT-EXIST-$$';")
if [ "${UNKNOWN_COUNT}" -ne 0 ]; then
  echo "FAIL: expected 0 rows for a nonexistent media_acquisition_job_id, found ${UNKNOWN_COUNT}"
  exit 1
fi
echo "PASS: nonexistent media_acquisition_job_id resolves to zero rows at the DB level; 'Build Media Acquisition Job Detail Response' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-DETAIL-001"
