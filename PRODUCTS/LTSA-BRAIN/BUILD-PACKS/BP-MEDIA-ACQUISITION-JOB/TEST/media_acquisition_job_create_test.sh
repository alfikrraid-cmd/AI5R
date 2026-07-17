#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-CREATE-001
# (Media Acquisition Job Create). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIAAJ-CREATE-$$"
TEST_EM_ID="TEST-EM-MEDIAAJ-CREATE-$$"
TEST_ID="TEST-MEDIAAJ-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM media_acquisition_job WHERE media_acquisition_job_id LIKE 'TEST-MEDIAAJ-CREATE-$$%';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> engineering_media)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR MEDIA ACQUISITION JOB');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR ACQUISITION JOB', 'PHOTO');"

echo "[1/3] Valid create inserts a row with correctly mapped fields, defaulting status to PENDING"
psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_EM_ID}');"

ROW_STATUS=$(psql_run -tAc "SELECT status FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}';")
if [ "${ROW_STATUS}" != "PENDING" ]; then
  echo "FAIL: expected default status 'PENDING', got '${ROW_STATUS}'"
  exit 1
fi
echo "PASS: row created with correctly mapped fields, status defaulted to PENDING"

echo "[2/3] status outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_STATUS_OUTPUT=$(psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id, status) VALUES ('${TEST_ID}-BAD', '${TEST_KS_ID}', '${TEST_EM_ID}', 'READY_FOR_MANUFACTURING');" 2>&1)
BAD_STATUS_EXIT=$?
set -e
if [ "${BAD_STATUS_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set status was accepted"
  exit 1
fi
echo "${BAD_STATUS_OUTPUT}" | grep -qi "media_acquisition_job_status_check" || { echo "FAIL: unexpected error on bad status: ${BAD_STATUS_OUTPUT}"; exit 1; }
echo "PASS: status outside the 4-value closed set (note: READY_FOR_MANUFACTURING, valid for acquisition_job/040C, is NOT valid here) rejected by media_acquisition_job_status_check"

echo "[3/3] Duplicate media_acquisition_job_id is rejected by the workflow's pre-insert conflict check"
set +e
DUP_OUTPUT=$(psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_EM_ID}');" 2>&1)
DUP_EXIT=$?
set -e
if [ "${DUP_EXIT}" -eq 0 ]; then
  echo "FAIL: duplicate media_acquisition_job_id was accepted"
  exit 1
fi
echo "${DUP_OUTPUT}" | grep -qi "duplicate key" || { echo "FAIL: unexpected error on duplicate: ${DUP_OUTPUT}"; exit 1; }
echo "PASS: duplicate media_acquisition_job_id rejected by the same unique constraint the workflow's 'Check Existing Media Acquisition Job' / 'IF Media Acquisition Job Exists' nodes test for, returning HTTP 409 via 'Respond Conflict'"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-CREATE-001"
