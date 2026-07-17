# BP-WORK-ORDER — Work Order

Manufacturing Order: MO-001 (OSA Maintenance v0.1)
Status: MANUFACTURED (structurally validated; runtime verification blocked — see MO-001 Manufacturing Report)

Maintenance work orders against any asset in the product (pump, seal, general asset, or soot blower), plus an optional customer reference. Built following the same conflict-check-on-create pattern as Seal, Asset, and Soot Blower Registries.

## Contents

- `DATABASE/001_create_table.sql`, `002_seed.sql`, `003_indexes.sql` — canonical `work_order` table, also mirrored in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`.
- `SCHEMAS/work_order.schema.json` — JSON Schema for the `WORK_ORDER` payload.
- `WORKFLOWS/WF-LTSA-BRAIN-WORK-ORDER-{CREATE,DETAIL,LIST,UPDATE,DELETE}-001.json` — five n8n workflows, real embedded SQL, no stub logic.
- `TEST/work_order_{create,detail,list,update,delete}_test.sh` — database-level functional tests, discovered automatically by `VERIFICATION/run_verification.sh`.

## Identifier and Relationships

`work_order_code` (TEXT primary key). `customer_code` references `customer_registry.customer_code` informally (no DB-level FK — see the documented rationale in `DATABASE/001_create_table.sql`). `asset_code` + `asset_type` is a polymorphic pair identifying which of the four registries (`pump_registry` / `ltsa_pumps`, `seal_registry`, `asset_registry`, `soot_blower_registry`) the referenced asset lives in — resolved at the application/workflow layer, not enforced by a database foreign key, since no common supertype table exists across those four registries in this schema. Introducing one would be new architecture, out of MO-001's scope.
