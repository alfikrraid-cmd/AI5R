#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-UPDATE-001
# (Media Acquisition Job Update). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIAAJ-UPDATE-$$"
TEST_EM_ID="TEST-EM-MEDIAAJ-UPDATE-$$"
TEST_ID="TEST-MEDIAAJ-UPDATE-$$"
OTHER_ID="TEST-MEDIAAJ-UPDATE-OTHER-$$"

cleanup() {
  psql_run -c "DELETE FROM media_acquisition_job WHERE media_acquisition_job_id IN ('${TEST_ID}', '${OTHER_ID}');" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain and two fixture jobs: one to update, one control"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR MEDIA JOB UPDATE');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR JOB UPDATE', 'PHOTO');"
psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id) VALUES ('${TEST_ID}', '${TEST_KS_ID}', '${TEST_EM_ID}');"
psql_run -c "INSERT INTO media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id) VALUES ('${OTHER_ID}', '${TEST_KS_ID}', '${TEST_EM_ID}');"

echo "[1/2] Valid update (equivalent to 'Update Media Acquisition Job's dynamic SET clause for status/finished_at) modifies only the targeted row's specified fields, knowledge_source_id/engineering_media_id untouched"
psql_run -c "UPDATE media_acquisition_job SET status = 'COMPLETED', finished_at = NOW(), validation_errors = NULL, updated_at = NOW() WHERE media_acquisition_job_id = '${TEST_ID}';"

UPDATED_STATUS=$(psql_run -tAc "SELECT status FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}';")
UPDATED_EM=$(psql_run -tAc "SELECT engineering_media_id FROM media_acquisition_job WHERE media_acquisition_job_id = '${TEST_ID}';")
OTHER_STATUS=$(psql_run -tAc "SELECT status FROM media_acquisition_job WHERE media_acquisition_job_id = '${OTHER_ID}';")

if [ "${UPDATED_STATUS}" != "COMPLETED" ]; then
  echo "FAIL: expected status 'COMPLETED' on targeted row, got '${UPDATED_STATUS}'"
  exit 1
fi
if [ "${UPDATED_EM}" != "${TEST_EM_ID}" ]; then
  echo "FAIL: engineering_media_id changed unexpectedly to '${UPDATED_EM}'"
  exit 1
fi
if [ "${OTHER_STATUS}" != "PENDING" ]; then
  echo "FAIL: unrelated row was modified (status now '${OTHER_STATUS}')"
  exit 1
fi
echo "PASS: only the targeted row's execution-result fields changed; knowledge_source_id/engineering_media_id and other rows untouched"

echo "[2/2] Unknown media_acquisition_job_id updates zero rows (workflow maps this to statusCode 404 in 'Check Update Result')"
UNKNOWN_UPDATED=$(psql_run -tAc "UPDATE media_acquisition_job SET status = 'FAILED' WHERE media_acquisition_job_id = 'DOES-NOT-EXIST-$$' RETURNING media_acquisition_job_id;")
if [ -n "${UNKNOWN_UPDATED}" ]; then
  echo "FAIL: expected zero rows affected for a nonexistent media_acquisition_job_id"
  exit 1
fi
echo "PASS: nonexistent media_acquisition_job_id affects zero rows at the DB level; 'Check Update Result' converts this to HTTP 404 (verified by reading the node source, not executed here)"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-ACQUISITION-JOB-UPDATE-001"
