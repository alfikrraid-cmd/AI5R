# AI5R Runtime Disaster Recovery Runbook

## Canonical Commands

- Backup: `python CORE-SERVICES/RUNTIME/backup.py --env-file <env> --compose-file CORE-SERVICES/RUNTIME/compose.yaml`
- Validate backup: `python CORE-SERVICES/RUNTIME/validate_backup.py <backup-id> --env-file <env>`
- Restore: `python CORE-SERVICES/RUNTIME/restore.py <backup-id> --env-file <env> --compose-file CORE-SERVICES/RUNTIME/compose.yaml --yes`
- Health: `python CORE-SERVICES/RUNTIME/healthcheck.py --env-file <env> --compose-file CORE-SERVICES/RUNTIME/compose.yaml`

## Service Backup Mechanisms

- PostgreSQL: logical `pg_dump` custom-format archive with database creation metadata.
- Neo4j Community: controlled offline filesystem archive after stopping the service; online enterprise backup is not available in the pinned edition.
- Redis: AOF-backed persistent volume archived only after `BGREWRITEAOF` completes and the service is quiesced.
- n8n: controlled offline volume archive reusing the existing `CORE-SERVICES/N8N` volume-backup semantics; supplemental workflow export is included when workflows exist.
- MinIO: controlled offline filesystem archive of the single-node object-data volume.
- Configuration: split portable and secret environment snapshots plus compose metadata.

## Recovery Scenarios

### Scenario A: Single Container Failure

1. Inspect `docker compose ps` and container logs.
2. Restart or recreate only the failed service.
3. Run canonical healthcheck.
4. Restore is not required unless the service data is corrupt.

### Scenario B: Bad Application Deployment

1. Roll back the dashboard/API image release or compose revision.
2. Rebuild/redeploy the prior known-good version.
3. Run canonical healthcheck.
4. Do not restore data unless persistent state was actually damaged.

### Scenario C: Database Corruption

1. Stop the runtime.
2. Validate the intended backup set.
3. Run canonical restore against the backup.
4. Start runtime and run canonical healthcheck.
5. Verify business data markers or smoke-test queries.

### Scenario D: Host Disk / Server Failure

1. Provision a replacement host with Docker Engine and Docker Compose.
2. Deploy the same AI5R runtime package version.
3. Restore protected configuration and secret material from backup storage.
4. Copy or mount the validated backup set onto the host.
5. Run canonical restore.
6. Run canonical healthcheck and service-specific validation.

### Scenario E: VPS Lost Completely

Follow Scenario D. A same-host-only backup is insufficient; off-host copies are mandatory for this event.

### Scenario F: Customer Server Replacement

1. Prepare compatible replacement server.
2. Install Docker and the matching AI5R runtime package version.
3. Restore portable configuration and protected secrets.
4. Transfer the validated backup set.
5. Run canonical restore and healthcheck.

## Initial Operational Targets

- Backup frequency: at least daily full backup.
- Retention: keep 14 days by default unless deployment policy requires more.
- RPO: up to 24 hours with daily backup scheduling.
- RTO: 30-90 minutes for a practiced single-host restore, depending on data size and image availability.
- Restore verification: perform a controlled restore drill at least monthly and after any material runtime-storage change.
- Off-host policy: maintain a local operational backup plus a copied or mounted off-host backup location.

## Off-Host Backup Policy

- `AI5R_BACKUP_ROOT` may point to any mounted storage path.
- Production policy should be:
  - local backup for fast operational recovery
  - off-host copy for host-loss disaster recovery
- If backup encryption is not implemented in the runtime, the storage location must provide encryption at rest and access control externally.

## Secret Handling

- `configuration/runtime.env.public` contains non-secret runtime settings.
- `configuration/runtime.env.secrets` contains required secret values for recovery.
- Manifest files never inline secret values.
- Backup operators must protect the backup directory and any off-host copy with host or storage encryption and restricted access.
