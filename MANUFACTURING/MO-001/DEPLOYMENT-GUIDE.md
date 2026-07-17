# MO-001 — OSA Maintenance v0.1 — Deployment Guide

Manufacturing Order: MO-001
Product: OSA Maintenance v0.1 (manufactured as `PRODUCTS/LTSA-BRAIN`)
Customer: CV Razzan Teknik Mandiri

This guide describes how to stand up OSA Maintenance v0.1 for internal demonstration and use. It assumes the same two external dependencies every prior LTSA-BRAIN MWO has assumed: a reachable PostgreSQL instance and a reachable n8n instance. Neither is provisioned by this repository (confirmed across MWO-P-001 through MWO-P-006); both must be supplied by whoever deploys this product.

## 1. Database

1. Provision a PostgreSQL instance (PostgreSQL 17 was used throughout this product's development).
2. Apply the canonical schema:
   ```
   psql "$LTSA_TEST_DSN" -f PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql
   ```
   This creates `customer_registry`, `ltsa_pumps`, `seal_registry`, and — new in MO-001 — `asset_registry`, `soot_blower_registry`, `work_order`, and `maintenance_history`. It is idempotent (every statement uses `IF NOT EXISTS`), matching the convention established in `VERIFICATION/bootstrap_schema.sh` (MWO-P-006).
3. Alternatively, apply each `BUILD-PACKS/BP-*/DATABASE/*.sql` file individually per module, in numeric order (`001_create_table.sql`, `002_seed.sql`, `003_indexes.sql`).

## 2. n8n

1. Provision or point at a reachable n8n instance.
2. Configure a PostgreSQL credential in n8n matching the credential ID already referenced throughout this product's workflows (`hzgFaX04t1nL01vF` — the same convention used since MWO-P-002).
3. Import every workflow JSON file under `BUILD-PACKS/BP-*/WORKFLOWS/*.json`, including the four new modules manufactured under MO-001 (`BP-ASSET`, `BP-SOOT-BLOWER`, `BP-WORK-ORDER`, `BP-MAINTENANCE-HISTORY`) and the new `BP-DASHBOARD` aggregation workflow.
4. Activate each imported workflow.

## 3. Dashboard

Open `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-DASHBOARD/dashboard.html` directly in a browser (no build step, no server required). Set the "n8n base URL" field to your n8n instance's webhook base (e.g. `http://localhost:5678/webhook`) and click "Load Summary".

## 4. Basic AI Assistant

No deployment step is required beyond having Python available — this module has no external service dependency:
```
python PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py
```
Import `get_maintenance_recommendation()` from `maintenance_assistant.py` into any calling code (e.g. a future n8n Code node, or a future Work Order workflow) to attach a BRAIN-generated recommendation to a maintenance observation.

## 5. Known Limitation — Runtime Verification

Every n8n/PostgreSQL-backed module in this order (Asset, Soot Blower, Work Order, Maintenance History, Dashboard) was structurally validated (shell syntax, JSON validity) but **not** executed against a live database during manufacturing — no credentialed PostgreSQL connection was available in the manufacturing session, the same standing condition documented since MWO-P-006/RV-004. Whoever deploys this product should run `VERIFICATION/run_verification.sh` (with `LTSA_TEST_DSN` set to a real, schema-applied database) as the first post-deployment step, and treat a clean run as the actual confirmation this guide cannot itself provide.

The Basic AI Assistant module is the one exception — it was actually executed during manufacturing (see `MO-001-MANUFACTURING-REPORT.md`), since it has no external dependency.
