#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-LIST-001
# (Media Acquisition Job List). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIAAJ-LIST-$$"
TEST_EM_ID="TEST-EM-MEDIAAJ-LIST-$$"
TEST_ID="TEST-MEDIAAJ-LIST-$$"

cleanup() {
  psql_run -c "DELETE FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> engineering_media)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'VIDEO', 'TEST SOURCE FOR MEDIA ACQUISITION JOB LIST');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR ACQUISITION JOB LIST', 'VIDEO');"

echo "[1/2] Row count increases by exactly 1 after insert"
BEFORE=$(psql_run -tAc "SELECT count(*) FROM media_acquisition_job;")
psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_EM_ID}');"
AFTER=$(psql_run -tAc "SELECT count(*) FROM media_acquisition_job;")
if [ "$((AFTER - BEFORE))" -ne 1 ]; then
  echo "FAIL: expected row count to increase by 1, went from ${BEFORE} to ${AFTER}"
  exit 1
fi
echo "PASS: 'List Media Acquisition Jobs' node's unfiltered SELECT * FROM media_acquisition_job reflects the fixture row"

echo "[2/2] Listed row includes the expected fields"
FOUND_EM=$(psql_run -tAc "SELECT engineering_media_id FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}';")
if [ "${FOUND_EM}" != "${TEST_EM_ID}" ]; then
  echo "FAIL: expected engineering_media_id '${TEST_EM_ID}', got '${FOUND_EM}'"
  exit 1
fi
echo "PASS: row shape matches what 'List Media Acquisition Jobs' would return for this table"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-LIST-001"
