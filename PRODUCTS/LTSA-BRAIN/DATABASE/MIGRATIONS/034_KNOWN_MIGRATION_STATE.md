# Known Migration State (as of MWO-LTSA-069, 2026-09-11)

Companion to `034_create_schema_migration_history.sql`. This is a
snapshot of what MWO-LTSA-069's read-only production audit could and
could not establish about migrations 005-034 -- it is NOT a claim that
this repository knows the true applied state of every migration.

**Rule this document follows:** if the audit did not directly verify a
fact, it is recorded as `UNKNOWN`, never inferred from "the file exists"
or "later migrations reference it." Do not upgrade any row below to
`CONFIRMED_APPLIED` without an equally direct check.

| Migration | Status | Basis |
|---|---|---|
| 005-031 | `UNKNOWN` | Not checked by this MWO (out of scope -- this audit targeted the group-agent/authorization area only). No schema-migration tracking existed before `034_create_schema_migration_history.sql`, so no prior record to consult either. |
| `032_create_whatsapp_group_authorization.sql` | `CONFIRMED_APPLIED` | Directly verified 2026-09-11 via read-only `docker exec ai5ros-prod-postgres-1 psql -d ltsa_brain -c '\dt public.whatsapp_group*'` against the production database: both `public.whatsapp_group_authorization` and `public.whatsapp_group_message_seen` exist, the former holding 2 real `ACTIVE` rows, the latter 45 real dedupe rows. This directly contradicts the migration file's own header comment ("NOT applied to production by this MWO") -- see the correction note added to that file. Applied out-of-band; by whom/when is itself `UNKNOWN`. |
| `033_add_pm_schedule_planned_activities.sql` | `UNKNOWN` | Not checked by this MWO. |
| `034_create_schema_migration_history.sql` | `UNKNOWN` (not yet applied anywhere) | Authored by this MWO. Report/design only, per MWO-LTSA-069's "Do NOT modify production DB" instruction -- see that file's own header. |

## Operator Action (not performed by this MWO)

Once `034_create_schema_migration_history.sql` is actually applied to a
database (production or otherwise) by an authorized operator, that
operator should also insert one row per migration reflecting this
document's findings at that time -- for example (illustrative, not
executed here):

```sql
INSERT INTO public.schema_migration_history
    (migration_file, status, applied_at, recorded_by, verification_note)
VALUES
    ('032_create_whatsapp_group_authorization.sql', 'CONFIRMED_APPLIED', NULL,
     'MWO-LTSA-069', 'Verified 2026-09-11 via docker exec psql; applied_at itself unknown, not fabricated.'),
    ('033_add_pm_schedule_planned_activities.sql', 'UNKNOWN', NULL,
     'MWO-LTSA-069', 'Not checked.');
-- 005-031 intentionally omitted: recording them as UNKNOWN rows adds no
-- information over their simple absence from this table. Add a row only
-- once a migration's status is actually known, one way or the other.
```

`applied_at` is left `NULL` for `032` above deliberately -- the audit
established *that* it is applied, not *when*. Do not backfill a plausible
guess.

## Why 005-031 Are Not Marked `ASSUMED_APPLIED_SEQUENTIAL`

That status exists in the schema for a database with a real migration
runner that enforces ordering. No such runner was found in this
repository (confirmed by MWO-LTSA-069's own investigation: no
`schema_migrations`-style table existed anywhere before this MWO). Absent
a runner, "032 turned out to be applied" is not evidence that 005-031
were applied *in order* by *that same mechanism* -- 032 is now known to
have been applied out-of-band, which is direct evidence the normal
assumption (sequential, tracked application) does not hold here. `UNKNOWN`
is the honest status until someone directly checks.

## Migrations 040-048: Reserved Archived R4 Quarantine (as of LTSA_POWER_BI_R1C)

Migrations 040 through 048 were authored on an unreviewed feature branch and executed in production out-of-band during `LTSA_R4_PRODUCTION_BACKUP_AND_MIGRATION_R1` before the release line was formally recovered to commit `0254379deeaa524f3d707d5e3df3c3c473da9e27`.

These migrations are preserved in `archive/ltsa-unified-r4-2af84e4` and quarantined from the governed release branch (`release/ltsa-v1-rc1`):
- `040_create_ltsa_contract_scope.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `041_create_ltsa_finding_and_cm_measurement.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `042_create_engineering_drawing.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `043_create_engineering_drawing_attribute.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `044_create_engineering_drawing_promotion.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `045_add_condition_monitoring_reading_field_form_idempotency.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `046_document_mechanical_seal_stock_pool.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `047_add_seal_registry_identity_and_type.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`
- `048_backfill_seal_registry_identity_and_type.sql`: `RESERVED_ARCHIVED_R4_QUARANTINE`

**Governance Rule:** These migrations are NOT dependencies of Power BI R1C (`049_create_ltsa_bi_machine_credentials.sql`). Their sequence slots are permanently reserved to prevent numbering collisions and avoid rewriting production history. In particular, migration 048's synthetic mechanical seal backfill (`MS-JC-XXXX`) is unreviewed and must NEVER be consumed or legitimized by R1C.

