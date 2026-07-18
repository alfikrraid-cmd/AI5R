# N8N — CORE-SERVICES

n8n workflow automation service for AI5R. This folder is the **single
canonical location** for n8n's Docker configuration, workflow exports, and
backup tooling — it follows the same per-module layout as every other
`CORE-SERVICES/<NAME>/` service in this repository.

```
CORE-SERVICES/N8N/
├── docker-compose.yml       # container definition (existing, unchanged)
├── README.md                # this file
├── credentials.example.md   # credential documentation template (no secrets)
├── backup-workflows.bat     # full raw export (CLI) of every workflow to WORKFLOWS/
├── backup-volume.bat        # snapshots the n8n data volume to BACKUPS/
├── restore-volume.bat       # restores the n8n data volume from a snapshot
├── export-workflows.bat     # Pack Manager: export one pack via the n8n REST API
├── import-workflows.bat     # Pack Manager: import one pack via the n8n REST API
├── validate-workflows.bat   # Pack Manager: validate pack manifests offline
├── list-workflows.bat       # Pack Manager: list pack contents offline
├── update-registry.bat      # Workflow Registry: scan + regenerate registry.json
├── export-workflows.ps1     # PowerShell implementation behind export-workflows.bat
├── import-workflows.ps1     # PowerShell implementation behind import-workflows.bat
├── validate-workflows.ps1   # PowerShell implementation behind validate-workflows.bat
├── list-workflows.ps1       # PowerShell implementation behind list-workflows.bat
├── update-registry.ps1      # PowerShell implementation behind update-registry.bat
├── registry.json            # Workflow Registry: generated index of all pack manifests
├── WORKFLOWS/                # exported workflow JSON (committed to git)
│   ├── manifest.json          # Pack Manager root index (per-pack counts/timestamps)
│   ├── COMMON/manifest.json    # pack: shared workflows across products
│   ├── LTSA/manifest.json      # pack: LTSA product workflows
│   ├── AUDITOR/manifest.json   # pack: AUDITOR product workflows
│   ├── SCHOOL/manifest.json    # pack: SCHOOL product workflows
│   └── UMKM/manifest.json      # pack: UMKM product workflows
└── BACKUPS/                  # volume archives (git-ignored, see BACKUPS/.gitignore)
```

## 1. Start Docker

From this folder:

```bat
cd CORE-SERVICES\N8N
docker compose up -d
```

This starts a container named `ai5r-n8n`, exposing n8n at
**http://localhost:5678**.

To stop it:

```bat
docker compose down
```

(`docker compose down` removes the container but not the named volume, so
workflow/credential data is preserved.)

## 2. First-time owner account

On first launch with an empty volume, n8n shows an owner-account setup
screen at http://localhost:5678. See `credentials.example.md` for the
template used to document (not store) that account and any per-workflow
credentials.

## 3. Docker volume

`docker-compose.yml` declares a volume named `n8n_data` mounted at
`/home/node/.n8n` inside the container — this is where n8n stores its
SQLite database (workflows, credentials, execution history) and settings.

Because the compose file does not pin an explicit external volume name,
Docker Compose prefixes it with the **project name** (derived from the
directory `docker compose` is run from, or `COMPOSE_PROJECT_NAME` if set).
To find the actual volume name on this machine:

```bat
docker inspect ai5r-n8n --format "{{range .Mounts}}{{.Name}} -> {{.Destination}}{{end}}"
```

`backup-volume.bat` and `restore-volume.bat` discover this name
automatically at run time — you never need to hardcode it.

## 4. Export workflows

```bat
backup-workflows.bat
```

Runs `n8n export:workflow --all --separate` inside the container and copies
the resulting JSON files into `WORKFLOWS/`. These files are safe to commit —
credentials are referenced by ID, not by decrypted value.

## 5. Back up the volume

```bat
backup-volume.bat
```

Creates a timestamped `n8n_data_<timestamp>.tar.gz` in `BACKUPS/` containing
the full contents of the n8n data volume (workflows, credentials, execution
history, settings). This is a superset of a workflow export — use it before
upgrades or migrations. Archives are git-ignored; copy them somewhere safe
(encrypted storage / offsite) if they need to survive beyond this machine.

## 6. Restore the volume

```bat
restore-volume.bat n8n_data_20260101_120000.tar.gz
```

Run with no arguments to list available backups in `BACKUPS/`. This is
**destructive** — it replaces all current volume data with the archive's
contents, and prompts for `YES` confirmation before proceeding. It stops the
container, restores the data, then restarts the container.

## 7. Deploy to a VPS

1. Copy this entire `CORE-SERVICES/N8N/` folder to the VPS (or `git pull` the
   repo there).
2. Install Docker + Docker Compose on the VPS.
3. Edit `docker-compose.yml` environment values for the public deployment:
   - `N8N_PROTOCOL=https` (once TLS is in front of n8n)
   - `WEBHOOK_URL=https://<your-domain>/`
   - Put n8n behind a reverse proxy (nginx / Caddy / Traefik) that terminates
     TLS and forwards to port `5678` — not covered by this compose file.
4. Bring it up: `docker compose up -d`.
5. If migrating existing data rather than starting fresh, copy a backup
   archive from `BACKUPS/` to the VPS and run `restore-volume.bat`
   (or the equivalent manual `docker run ... tar xzf ...` commands) **before**
   pointing DNS/traffic at the new instance.
6. Re-run `backup-workflows.bat` / `backup-volume.bat` on whatever schedule
   fits (cron on the VPS, or a scheduled task) to keep backups current.

## 8. Workflow Pack Manager

A **pack** is a named group of workflows exported/imported together —
`COMMON`, `LTSA`, `AUDITOR`, `SCHOOL`, or `UMKM` — each with its own folder
under `WORKFLOWS/` and its own `manifest.json`. Unlike `backup-workflows.bat`
(a full raw CLI export of everything, used for disaster recovery), the Pack
Manager talks to the **n8n REST API** and lets you export/import one product
line at a time.

**How packs are matched:** a workflow belongs to a pack if it has an n8n tag
with the exact same name (e.g. tag a workflow `LTSA` in the n8n UI to include
it in `export-workflows.bat LTSA`). Tag your workflows in n8n before running
an export.

**Prerequisites:**

1. Complete the owner account setup (§2).
2. In n8n, go to **Settings → API → Create an API Key**.
3. Set it for your shell session:
   ```bat
   set N8N_API_KEY=your-key-here
   ```
   (Optionally `set N8N_URL=http://localhost:5678` if not using the default.)

**Commands** (run from `CORE-SERVICES/N8N/`):

```bat
list-workflows.bat                REM list all packs (offline, reads manifests)
list-workflows.bat LTSA           REM list one pack

validate-workflows.bat            REM validate all packs: manifest vs. files on disk
validate-workflows.bat LTSA       REM validate one pack

export-workflows.bat LTSA         REM pull workflows tagged "LTSA" from n8n -> WORKFLOWS\LTSA\
import-workflows.bat LTSA         REM push WORKFLOWS\LTSA\ workflows into n8n (create/update by name)
import-workflows.bat LTSA --activate   REM ...and activate each one after import
```

`list-workflows.bat` and `validate-workflows.bat` work fully offline (they
only read the manifests on disk); `export-workflows.bat` and
`import-workflows.bat` require `N8N_API_KEY` and a reachable n8n instance.

**Notes / known limitations:**

- Import matches existing workflows **by name**, not by ID, since workflow
  IDs are environment-specific (e.g. differ between local and VPS). Two
  workflows with the same name in the same n8n instance will be treated as
  the same workflow on re-import.
- Tag assignment during import is best-effort: n8n's tag API has changed
  shape across versions, so a tagging failure is logged as a `[WARN]`, not a
  failed import — check tags manually in the UI if you see that warning.
- These endpoints assume n8n's Public REST API v1 (`/api/v1/...`), available
  in recent n8n versions. If your image is older, the API paths may differ.

## 9. Workflow Registry

`registry.json` (at the root of this folder) is a **generated, read-only
index** aggregating every pack's `manifest.json` under `WORKFLOWS/`. Unlike
`WORKFLOWS/manifest.json` (the Pack Manager's own root index, updated
in-place by `export-workflows.bat`), `registry.json` is rebuilt from scratch
by scanning `WORKFLOWS/*/manifest.json` on disk — it discovers pack folders
dynamically rather than relying on a hardcoded pack list, so it also serves
as an integrity check across all packs.

```bat
update-registry.bat
```

For each pack folder it validates:

- **missing manifest** — pack folder has no `manifest.json`
- **malformed JSON** — `manifest.json` fails to parse
- **invalid version** — `manifestVersion` is present but not the supported value (currently `1`)
- **duplicate pack** — two folders declare the same `"pack"` name
- **duplicate manifest entry** — the same workflow (`id`, or `file` if no `id`) appears in more than one pack's `workflows` list

If any pack fails validation, `registry.json` is **left untouched** (not
partially overwritten) and the script exits non-zero — fix the offending
manifest and re-run. `registry.json` is fully offline and does not call the
n8n REST API; do not hand-edit it, since the next `update-registry.bat` run
overwrites it.

## Notes

- This folder's layout intentionally mirrors sibling modules under
  `CORE-SERVICES/` (`API/`, `BACKEND-API/`, `MODULE-MANAGER/`, etc.) rather
  than introducing a new top-level structure — see `ADR/ADR-000-Architecture-Governance.md`
  for why canonical location matters in this repo.
- No business workflow content, application code, or the existing
  `docker-compose.yml` was modified to add this tooling.
