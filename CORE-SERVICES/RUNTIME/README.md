# OSA Runtime Core Package

`CORE-SERVICES/RUNTIME` is also the canonical home for the enterprise
runtime operations foundation introduced by `MWO-RUNTIME-OPS-002`.

That operations layer is intentionally separate from the application
runtime chain:

`ProductRuntime -> ProductRegistry -> OSA.RuntimePipeline`

The files added here package and observe the existing application stack
without moving Docker, Compose, health, or infrastructure concerns into
`ProductRuntime`.

## Enterprise Operations Foundation

- `.env.example`: one canonical environment contract for dashboard, API,
  PostgreSQL, Neo4j, Redis, n8n, MinIO, Nginx, and Gotenberg.
- `compose.yaml`: one portable Docker Compose bundle for the full runtime
  installation.
- `docker/`: packaging assets for the existing dashboard and FastAPI
  application, plus `nginx-proxy.conf` (the edge reverse-proxy config).
- `validate_config.py`: one reusable configuration validator.
- `healthcheck.py`: one canonical operator health entrypoint.
- `ops_common.py`: shared loading, validation, and compose helpers used by
  operations scripts.

### Edge reverse proxy (`nginx`) -- MWO-AI5R-105

One additional, unified entrypoint (`AI5R_NGINX_PORT`, default `8080`) in
front of the existing `dashboard`/`api`/`n8n` services: `/api/*` is
forwarded to `api:8000` unchanged (every backend route already starts with
`/api/`, so no path rewriting happens), n8n bootstrap/API paths under
`/rest/*` and active workflow paths under `/webhook/*` are forwarded to
`n8n:5678`, and everything else is forwarded to `dashboard:80` (the
existing built SPA, served by its own already-existing internal nginx,
unchanged). This is additive, not a replacement -- the compose nginx
remains the single public gateway behind host-owned TLS.

### Document conversion (`gotenberg`) -- MWO-AI5R-105

Documented in this repository's own root `MEMORY.md` as an intended
Production Runtime (VPS) responsibility, now actually present in
`compose.yaml`. Stateless, internal-only (`backend` network, no published
port) -- no application code calls it yet, so it is not exposed publicly;
wiring a real caller to it is a separate, future mission.

## Backup And Recovery

- `backup.py`: canonical backup entrypoint for PostgreSQL, Neo4j, Redis,
  n8n, MinIO, and runtime configuration.
- `validate_backup.py`: manifest and checksum validation for backup sets.
- `restore.py`: canonical destructive restore entrypoint with preflight
  validation and post-restore health check.
- `backup_restore_common.py`: shared manifest, checksum, retention, and
  configuration snapshot logic.
- `BACKUPS/`: default local backup root for timestamped runtime backup sets.
- `DISASTER_RECOVERY_RUNBOOK.md`: operator recovery procedures, RPO/RTO,
  and off-host backup policy.

Version: 1.1.0  
Status: FINAL PACKAGE CANDIDATE

This package makes OSA bootable as a modular runtime service package and
provides the canonical backup/restore path for host recovery.

## Workflows

- WF-OSA-RUNTIME-BOOT-001
- WF-OSA-RUNTIME-STATUS-001
- WF-OSA-RUNTIME-MODULES-001
- WF-OSA-RUNTIME-HEALTH-001
- WF-OSA-RUNTIME-EVENTS-001

## Important

GitHub is not required for runtime boot. PostgreSQL is the Single Source of Truth.
