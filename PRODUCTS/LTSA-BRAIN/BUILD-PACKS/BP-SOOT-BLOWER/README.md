# BP-SOOT-BLOWER — Soot Blower Registry

Manufacturing Order: MO-001 (OSA Maintenance v0.1)
Status: MANUFACTURED (structurally validated; runtime verification blocked — see MO-001 Manufacturing Report)

Boiler soot-blower equipment registry, built following the exact `BUILD-PACKS/BP-SEAL` convention (MWO-P-005): same DDL shape, same Create-conflict-check pattern, same test structure using `VERIFICATION/lib/psql_common.sh`.

## Contents

- `DATABASE/001_create_table.sql`, `002_seed.sql`, `003_indexes.sql` — canonical `soot_blower_registry` table, also mirrored in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`.
- `SCHEMAS/soot_blower.schema.json` — JSON Schema for the `SOOT_BLOWER` payload.
- `WORKFLOWS/WF-LTSA-BRAIN-SOOT-BLOWER-{CREATE,DETAIL,LIST,UPDATE,DELETE}-001.json` — five n8n workflows, real embedded SQL, no stub logic.
- `TEST/soot_blower_{create,detail,list,update,delete}_test.sh` — database-level functional tests, discovered automatically by `VERIFICATION/run_verification.sh`.

## Identifier

`soot_blower_code` (TEXT primary key), consistent with the TEXT-PK convention used by `seal_registry` and `asset_registry`.
