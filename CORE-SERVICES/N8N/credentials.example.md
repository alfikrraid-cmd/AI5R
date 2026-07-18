# n8n Credentials Reference (Template)

This file is a **template only** — it documents which credentials exist and
where they come from. It must never contain real secret values.

Copy this file to a local, git-ignored note (or a password manager entry) and
fill in real values there. Do not create a `credentials.md` in this repo.

---

## Owner Account

The first time n8n starts with an empty volume, it prompts for an owner
account at http://localhost:5678 (or the deployed URL). This is a one-time
setup screen.

| Field | Example / placeholder |
|---|---|
| Email | `owner@example.com` |
| First / Last name | `AI5R Admin` |
| Password | *(store in password manager, not here)* |

If the owner account already exists and you need to reset access, see n8n's
own user management documentation for the version you have deployed.

## Environment Variables (docker-compose.yml)

These are already set in `docker-compose.yml` and are not secret, but are
listed here for completeness:

| Variable | Purpose |
|---|---|
| `TZ` / `GENERIC_TIMEZONE` | Timezone used for scheduling and logs |
| `N8N_HOST` / `N8N_PORT` / `N8N_PROTOCOL` | Network binding |
| `WEBHOOK_URL` | Public base URL n8n advertises for webhook nodes |

## Per-Credential Nodes (fill in as workflows are built)

Each workflow-level credential (API keys, database logins, OAuth apps, etc.)
configured inside the n8n UI should be listed here by **name and purpose
only** — never the secret value itself:

| Credential name (in n8n) | Used by workflow(s) | Type | Owner / where the real secret lives |
|---|---|---|---|
| _(example)_ `AI5R-Postgres` | _(example)_ WF-OSA-REGISTRY-LOADER-001 | Postgres | Vault / password manager entry X |

## Notes

- n8n encrypts credential values at rest inside the `n8n_data` volume using a
  key also stored in that volume. A volume backup (`backup-volume.bat`)
  therefore can decrypt those credentials if restored elsewhere — treat
  backup archives in `BACKUPS/` as sensitive (they are already git-ignored).
- Workflow exports (`backup-workflows.bat` / `WORKFLOWS/*.json`) reference
  credentials by ID only, not by decrypted value, and are safe to commit.
