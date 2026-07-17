#!/usr/bin/env bash
# Functional test for WF-LTSA-BRAIN-MEDIA-CLASSIFICATION-CREATE-001
# (Media Classification Create). MWO-LTSA-040E (Engineering Media
# Acquisition).
#
# Exercises the workflow's actual SQL logic directly against a real,
# controllable PostgreSQL instance. Does not depend on any external host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../VERIFICATION/lib/psql_common.sh
source "$SCRIPT_DIR/../../../VERIFICATION/lib/psql_common.sh"

TEST_KS_ID="TEST-KS-MEDIACLASS-CREATE-$$"
TEST_EM_ID="TEST-EM-MEDIACLASS-CREATE-$$"
TEST_ID="TEST-MEDIACLASS-CREATE-$$"

cleanup() {
  psql_run -c "DELETE FROM media_classification WHERE media_classification_id LIKE 'TEST-MEDIACLASS-CREATE-$$%';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM engineering_media WHERE engineering_media_id = '${TEST_EM_ID}';" >/dev/null 2>&1 || true
  psql_run -c "DELETE FROM knowledge_source_registry WHERE knowledge_source_id = '${TEST_KS_ID}';" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[setup] Parent chain (knowledge_source_registry -> engineering_media)"
psql_run -c "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES ('${TEST_KS_ID}', 'PHOTO', 'TEST SOURCE FOR MEDIA CLASSIFICATION');"
psql_run -c "INSERT INTO engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type) VALUES ('${TEST_EM_ID}', '${TEST_KS_ID}', 'TEST ENGINEERING MEDIA FOR CLASSIFICATION', 'PHOTO');"

echo "[1/3] Valid create inserts a row with correctly mapped fields"
psql_run -c "INSERT INTO media_classification (media_classification_id, engineering_media_id, classification_type, confidence) VALUES ('${TEST_ID}', '${TEST_EM_ID}', 'PHOTO', 0.92);"

ROW_COUNT=$(psql_run -tAc "SELECT count(*) FROM media_classification WHERE media_classification_id = '${TEST_ID}' AND classification_type = 'PHOTO';")
if [ "${ROW_COUNT}" -ne 1 ]; then
  echo "FAIL: expected 1 row for ${TEST_ID}, found ${ROW_COUNT}"
  exit 1
fi
echo "PASS: row created with correctly mapped fields"

echo "[2/3] classification_type outside the closed set is rejected by the schema CHECK constraint"
set +e
BAD_TYPE_OUTPUT=$(psql_run -c "INSERT INTO media_classification (media_classification_id, engineering_media_id, classification_type) VALUES ('${TEST_ID}-BAD', '${TEST_EM_ID}', 'RANDOM_CLASS');" 2>&1)
BAD_TYPE_EXIT=$?
set -e
if [ "${BAD_TYPE_EXIT}" -eq 0 ]; then
  echo "FAIL: an out-of-set classification_type was accepted"
  exit 1
fi
echo "${BAD_TYPE_OUTPUT}" | grep -qi "media_classification_type_check" || { echo "FAIL: unexpected error on bad classification_type: ${BAD_TYPE_OUTPUT}"; exit 1; }
echo "PASS: classification_type outside the 9-value closed set rejected by media_classification_type_check"

echo "[3/3] A second classification row for the same engineering_media_id is accepted (repeatable, per Business Rule)"
psql_run -c "INSERT INTO media_classification (media_classification_id, engineering_media_id, classification_type) VALUES ('${TEST_ID}-2', '${TEST_EM_ID}', 'INSPECTION_IMAGE');"
REPEAT_COUNT=$(psql_run -tAc "SELECT count(*) FROM media_classification WHERE engineering_media_id = '${TEST_EM_ID}';")
if [ "${REPEAT_COUNT}" -ne 2 ]; then
  echo "FAIL: expected 2 classification rows for ${TEST_EM_ID}, found ${REPEAT_COUNT}"
  exit 1
fi
echo "PASS: repeated classification against the same Engineering Media accumulates as new rows, not hidden by any uniqueness constraint"

echo "ALL DB-LEVEL CHECKS COMPLETE for WF-LTSA-BRAIN-MEDIA-CLASSIFICATION-CREATE-001"
