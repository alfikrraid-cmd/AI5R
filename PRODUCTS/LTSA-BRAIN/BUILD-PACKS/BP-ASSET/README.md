# BP-ASSET — Asset Registry

Manufacturing Order: MO-001 (OSA Maintenance v0.1)
Status: MANUFACTURED (structurally validated; runtime verification blocked — see MO-001 Manufacturing Report)

General equipment registry — assets that are not Pumps or Seals (each of which already have their own registry: `MODULES/PUMP` / `BUILD-PACKS/BP-PUMP`, `BUILD-PACKS/BP-SEAL`). Built following the exact `BUILD-PACKS/BP-SEAL` convention established under MWO-P-005: same DDL shape, same Create-conflict-check pattern, same test structure using `VERIFICATION/lib/psql_common.sh`.

## Contents

- `DATABASE/001_create_table.sql`, `002_seed.sql`, `003_indexes.sql` — canonical `asset_registry` table, also mirrored in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`.
- `SCHEMAS/asset.schema.json` — JSON Schema for the `ASSET` payload.
- `WORKFLOWS/WF-LTSA-BRAIN-ASSET-{CREATE,DETAIL,LIST,UPDATE,DELETE}-001.json` — five n8n workflows, real embedded SQL, no stub logic.
- `TEST/asset_{create,detail,list,update,delete}_test.sh` — database-level functional tests, discovered automatically by `VERIFICATION/run_verification.sh`.

## Identifier

`asset_code` (TEXT primary key), following the same TEXT-PK convention as `seal_registry.seal_code` and `pump_registry.pump_code` — no surrogate UUID column, consistent with Seal.
