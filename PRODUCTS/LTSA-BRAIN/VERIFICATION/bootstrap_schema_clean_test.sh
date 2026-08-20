#!/usr/bin/env bash
# Verifies that CANONICAL_SCHEMA.sql bootstraps a completely empty database
# and remains safe to run a second time.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/../DATABASE/CANONICAL_SCHEMA.sql"

# shellcheck source=lib/psql_common.sh
source "$SCRIPT_DIR/lib/psql_common.sh"

if [ -z "$DSN" ]; then
  echo "FAIL: LTSA_TEST_DSN must point to a completely empty test database."
  exit 1
fi

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "FAIL: canonical schema file not found at $SCHEMA_FILE"
  exit 1
fi

USER_TABLE_COUNT="$(psql_run -tAc "
  SELECT count(*)
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';
")"
USER_TABLE_COUNT="${USER_TABLE_COUNT//[[:space:]]/}"

if [ "$USER_TABLE_COUNT" != "0" ]; then
  echo "FAIL: LTSA_TEST_DSN is not empty; found $USER_TABLE_COUNT public table(s)."
  echo "Refusing to modify a non-empty database for clean-bootstrap verification."
  exit 1
fi

echo "[bootstrap] Applying canonical schema to empty database..."
psql_run -f "$SCHEMA_FILE"

echo "[bootstrap] Reapplying canonical schema to prove rerun safety..."
psql_run -f "$SCHEMA_FILE"

MISSING_TABLE_COUNT="$(psql_run -tAc "
  WITH expected(table_name) AS (
    VALUES
      ('customer_registry'),
      ('ltsa_pumps'),
      ('seal_registry'),
      ('asset_registry'),
      ('soot_blower_registry'),
      ('work_order'),
      ('maintenance_history'),
      ('pm_schedule'),
      ('pm_occurrence'),
      ('cm_report'),
      ('condition_monitoring_schedule'),
      ('condition_monitoring_reading'),
      ('pm_cm_evidence'),
      ('knowledge_source_registry'),
      ('seal_stock'),
      ('seal_pump_compatibility'),
      ('seal_interchange_compatibility'),
      ('seal_engineering_document'),
      ('workbook'),
      ('worksheet'),
      ('worksheet_table'),
      ('mapping_profile'),
      ('column_mapping'),
      ('acquisition_job'),
      ('pdf_document'),
      ('pdf_metadata'),
      ('document_classification'),
      ('pdf_acquisition_job'),
      ('engineering_media'),
      ('media_metadata'),
      ('media_classification'),
      ('media_acquisition_job'),
      ('document_field_extraction')
  )
  SELECT count(*)
  FROM expected e
  LEFT JOIN information_schema.tables t
    ON t.table_schema = 'public'
   AND t.table_name = e.table_name
   AND t.table_type = 'BASE TABLE'
  WHERE t.table_name IS NULL;
")"
MISSING_TABLE_COUNT="${MISSING_TABLE_COUNT//[[:space:]]/}"

if [ "$MISSING_TABLE_COUNT" != "0" ]; then
  echo "FAIL: expected canonical table(s) are missing: $MISSING_TABLE_COUNT"
  exit 1
fi

MISSING_FK_COUNT="$(psql_run -tAc "
  WITH expected(child_table, parent_table) AS (
    VALUES
      ('seal_stock', 'seal_registry'),
      ('seal_pump_compatibility', 'seal_registry'),
      ('seal_pump_compatibility', 'ltsa_pumps'),
      ('seal_interchange_compatibility', 'seal_registry'),
      ('seal_engineering_document', 'seal_registry'),
      ('seal_engineering_document', 'knowledge_source_registry'),
      ('workbook', 'knowledge_source_registry'),
      ('worksheet', 'workbook'),
      ('worksheet_table', 'worksheet'),
      ('column_mapping', 'mapping_profile'),
      ('acquisition_job', 'workbook'),
      ('acquisition_job', 'mapping_profile'),
      ('pdf_document', 'knowledge_source_registry'),
      ('pdf_metadata', 'pdf_document'),
      ('document_classification', 'pdf_document'),
      ('pdf_acquisition_job', 'knowledge_source_registry'),
      ('pdf_acquisition_job', 'pdf_document'),
      ('engineering_media', 'knowledge_source_registry'),
      ('media_metadata', 'engineering_media'),
      ('media_classification', 'engineering_media'),
      ('media_acquisition_job', 'knowledge_source_registry'),
      ('media_acquisition_job', 'engineering_media'),
      ('document_field_extraction', 'ltsa_pumps'),
      ('document_field_extraction', 'seal_registry')
  ),
  actual AS (
    SELECT child.relname AS child_table,
           parent.relname AS parent_table
    FROM pg_constraint c
    JOIN pg_class child ON child.oid = c.conrelid
    JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
    JOIN pg_class parent ON parent.oid = c.confrelid
    JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
    WHERE c.contype = 'f'
      AND child_ns.nspname = 'public'
      AND parent_ns.nspname = 'public'
  )
  SELECT count(*)
  FROM expected e
  WHERE NOT EXISTS (
    SELECT 1
    FROM actual a
    WHERE a.child_table = e.child_table
      AND a.parent_table = e.parent_table
  );
")"
MISSING_FK_COUNT="${MISSING_FK_COUNT//[[:space:]]/}"

if [ "$MISSING_FK_COUNT" != "0" ]; then
  echo "FAIL: expected foreign-key relationship(s) are missing: $MISSING_FK_COUNT"
  exit 1
fi

DUPLICATE_TABLE_COUNT="$(psql_run -tAc "
  SELECT count(*)
  FROM (
    SELECT lower(table_name) AS canonical_name, count(*) AS table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    GROUP BY lower(table_name)
    HAVING count(*) > 1
  ) duplicates;
")"
DUPLICATE_TABLE_COUNT="${DUPLICATE_TABLE_COUNT//[[:space:]]/}"

if [ "$DUPLICATE_TABLE_COUNT" != "0" ]; then
  echo "FAIL: duplicate canonical table name(s) found: $DUPLICATE_TABLE_COUNT"
  exit 1
fi

echo "PASS: canonical schema clean bootstrap, rerun, canonical tables, foreign keys, and duplicate-table checks passed."
