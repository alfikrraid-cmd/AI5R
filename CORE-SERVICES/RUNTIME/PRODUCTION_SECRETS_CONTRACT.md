# AI5ROS Production Secrets Contract

Production secrets are host-owned operational material. The repository owns
only this contract and the non-secret example file; the real production
`.env` must live on the VPS or in the approved secret store.

## Required Secrets

| Variable | Owner | Rotation rule | Notes |
|---|---|---|---|
| `AI5R_POSTGRES_PASSWORD` | Production operator | Rotate before handover and after personnel/security events | Must match reused or migrated PostgreSQL. |
| `AI5R_NEO4J_PASSWORD` | Production operator | Rotate before enabling Neo4j production use | Required by canonical compose while Neo4j is retained. |
| `AI5R_REDIS_PASSWORD` | Production operator | Rotate before cutover | Must match reused or migrated Redis. |
| `AI5R_N8N_ENCRYPTION_KEY` | Production operator | Do not rotate casually after migration | Must match existing n8n key to decrypt migrated credentials. |
| `AI5R_MINIO_ROOT_PASSWORD` | Production operator | Rotate before public object storage use | Required if MinIO retains production data. |

## Handling Rules

- Do not commit the real production `.env`.
- Do not paste secrets into release reports, logs, screenshots, or tickets.
- Store production `.env` with owner-only permissions on the VPS.
- Backups created by `backup.py` include a protected secret snapshot; backup
  storage must be encrypted and access controlled externally.
- The n8n encryption key is data-critical. Losing it can make existing n8n
  credentials unrecoverable even if the volume backup is intact.

## Cutover Preflight

- Confirm every `REPLACE_WITH_...` placeholder is replaced on the host.
- Confirm `python CORE-SERVICES/RUNTIME/validate_config.py --env-file <prod-env>` passes.
- Confirm production-like env uses `AI5R_ENV=production`, not development.
- Confirm `AI5R_DOMAIN=osa-system.com` is host-only, not a URL.