# BP-DASHBOARD — Dashboard

Manufacturing Order: MO-001 (OSA Maintenance v0.1)
Status: MANUFACTURED (structurally validated; runtime verification blocked — see MO-001 Manufacturing Report)

A minimal, real aggregation endpoint plus a single static HTML demo page — deliberately not a framework application. No frontend framework exists anywhere in this repository to reuse (`MODULES/PUMP/UI/*.tsx` are confirmed 0-byte placeholders, per MWO-P-001), and introducing one would be new architecture, explicitly out of MO-001's scope (see `MANUFACTURING/MO-001/MO-001-SPECIFICATION.md`).

## Contents

- `WORKFLOWS/WF-LTSA-BRAIN-DASHBOARD-SUMMARY-001.json` — one n8n workflow (`GET /ltsa/dashboard/summary`) that counts rows across all six registries plus open Work Orders, via a single `UNION ALL` query.
- `TEST/dashboard_summary_test.sh` — exercises the exact embedded query against a real PostgreSQL instance.
- `dashboard.html` — a single, dependency-free static page that calls the summary endpoint via `fetch` and renders a table. Open directly in a browser; point the "n8n base URL" field at a running n8n instance.

## Scope Note

This is the Dashboard module's Minimum Manufacturable form: real counts, real query, real demonstrability — not a full application shell. Expanding it into a framework-based UI is future work, not part of this order.
