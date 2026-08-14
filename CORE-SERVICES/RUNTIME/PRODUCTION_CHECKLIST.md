# AI5ROS Production Checklist

## Reuse Audit

- [ ] Existing VPS reused.
- [ ] Existing system nginx reused for public TLS ingress.
- [ ] Existing certbot reused for certificate lifecycle.
- [ ] Existing PostgreSQL data reused or migrated into canonical runtime volume.
- [ ] Existing Redis data reused or migrated into canonical runtime volume.
- [ ] Existing n8n data/workflows/credentials migrated into canonical runtime volume.
- [ ] Existing Gotenberg capability retained as stateless canonical compose service.
- [ ] No legacy standalone n8n compose remains active after acceptance.
- [ ] No verify stack remains active after acceptance.

## Production Preparation

- [ ] Production `.env` created from `.env.production.example` on the VPS.
- [ ] Production `.env` keeps `AI5R_POSTGRES_DB=ai5r_runtime`, `AI5R_POSTGRES_PORT=5432`, and `AI5R_LTSA_POSTGRES_DB=ltsa_brain`.
- [ ] Real secrets satisfy `PRODUCTION_SECRETS_CONTRACT.md`.
- [ ] Image tags are pinned to approved release versions.
- [ ] `validate_config.py` passes against production `.env`.
- [ ] `docker compose config` passes against `compose.yaml`.
- [ ] Rendered n8n config uses PostgreSQL (`DB_TYPE=postgresdb`) and does not fall back to SQLite.
- [ ] System nginx config is backed up before cutover.
- [ ] Certbot certificate for `osa-system.com` is valid.
- [ ] Firewall exposes only intended public ports.

## Data And Backup

- [ ] Pre-cutover backup completed with `backup.py`.
- [ ] Backup validated with `validate_backup.py`.
- [ ] Restore drill completed in a non-production target or approved maintenance window.
- [ ] n8n encryption key confirmed before n8n volume migration.
- [ ] Off-host backup copy completed.

## Acceptance

- [ ] `healthcheck.py` returns healthy.
- [ ] `smoke_test.py` passes against `https://osa-system.com`.
- [ ] Dashboard resolves through system nginx.
- [ ] API resolves through system nginx.
- [ ] Direct dashboard/API container ports are not public.
- [ ] Rollback path is ready and documented.
