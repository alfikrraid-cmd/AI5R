# BP-MAINTENANCE-HISTORY — Maintenance History

Manufacturing Order: MO-001 (OSA Maintenance v0.1)
Status: MANUFACTURED (structurally validated; runtime verification blocked — see MO-001 Manufacturing Report)

Log of completed maintenance actions, optionally tied to a Work Order and to an asset in any of the four asset registries. Built following the same conflict-check-on-create pattern as the other new registries in this order.

## Contents

- `DATABASE/001_create_table.sql`, `002_seed.sql`, `003_indexes.sql` — canonical `maintenance_history` table, also mirrored in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`.
- `SCHEMAS/maintenance_history.schema.json` — JSON Schema for the `MAINTENANCE_HISTORY` payload.
- `WORKFLOWS/WF-LTSA-BRAIN-MAINTENANCE-HISTORY-{CREATE,DETAIL,LIST,UPDATE,DELETE}-001.json` — five n8n workflows, real embedded SQL, no stub logic.
- `TEST/maintenance_history_{create,detail,list,update,delete}_test.sh` — database-level functional tests, discovered automatically by `VERIFICATION/run_verification.sh`.

## Identifier and Relationships

`maintenance_record_code` (TEXT primary key). `work_order_code` and the `(asset_code, asset_type)` pair are both informal references (no DB-level FK), for the same documented reason as `BP-WORK-ORDER` — this also allows a maintenance record to exist without a formal Work Order (e.g. ad hoc maintenance performed and logged directly).
