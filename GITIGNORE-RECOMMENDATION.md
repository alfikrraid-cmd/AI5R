# .gitignore Recommendation

Status: Recommendation only. `.gitignore` has NOT been modified. No commit performed.
Requested by: Chief Architect — EOPS-003 Repository Hygiene mission, Task 2

---

## Current `.gitignore` (unchanged, for reference)

```
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.venv/
venv/
.DS_Store
_QUARANTINE_UNTRACKED/
```

This already correctly covers Python bytecode caches and common local-environment files. No entry currently covers build-cache/generated-artifact directories, local IDE/editor files, or local Claude Code configuration — the gaps this mission was asked to review.

---

## Recommended Additions

```
# Build cache / generated artifacts
BUILD/
PRODUCTS/*/RELEASE/

# Backup / scratch files
*.bak
*.bak.*
*.tmp
*.old
*~

# Local Claude Code configuration (per-machine, never shared)
.claude/

# IDE / editor local state (none currently found in this repo, added preemptively)
.vscode/
.idea/

# Node.js dependency trees (already absent from git status; added preemptively
# for any future JS-based product, since none of the existing ones are ignored
# today by the root .gitignore -- AI5R-STUDIO's own node_modules are excluded
# by AI5R-STUDIO/dashboard/.gitignore, a separate, nested file, not this one)
node_modules/
```

---

## Rationale, Per Entry

| Entry | Rationale | Evidence |
|---|---|---|
| `BUILD/` | 162 `RUN-<hash>` generated build-run directories, 819 files, ~913 KB — confirmed generated/temporary, not source (`RCA-002` §3). | Direct inspection this mission. |
| `PRODUCTS/*/RELEASE/` | Auto-regenerated stub schema/OpenAPI/SQL, confirmed mechanically produced by a test side effect, non-canonical (`RCA-001`, `RCA-002` §1–2). Scoped to `PRODUCTS/*/RELEASE/` rather than a bare `RELEASE/` so it does not accidentally also match `BLUEPRINT/`'s unrelated, real, hand-authored `README.md`'s mention of "release" concepts or any future per-product `RELEASE/` directory that turns out to hold real content — this pattern only matches the specific `RELEASE/` subdirectory of a product folder. |
| `*.bak`, `*.bak.*`, `*.tmp`, `*.old`, `*~` | Two `.bak` files already exist committed in history (`AI5R-SDK/FACTORY/MANUFACTURING/service.py.bak`, `.fm0015.bak`) and one more sits untracked at the repo root (`claude_desktop_config.json.bak.json`) — evidence this pattern of leaving backup files in the tree recurs. `.bak.*` specifically catches the double-extension case (`claude_desktop_config.json.bak.json`) that a plain `*.bak` would miss. | Direct inspection this mission (`git ls-files`, `find`). |
| `.claude/` | Two copies found (`.claude/`, `CONSTITUTION/.claude/`), each containing only `launch.json` and `settings.local.json` — both per-machine/personal by Claude Code's own naming convention, never intended for commit. | Direct inspection this mission. |
| `.vscode/`, `.idea/` | None found in this repository today — added preemptively since IDE local-state files are a near-universal source of accidental commits once any contributor opens the repo in VS Code or JetBrains, and adding the pattern now costs nothing. | Absence confirmed by direct search this mission; recommendation is precautionary, not evidence-driven like the others. |
| `node_modules/` | `AI5R-STUDIO/dashboard/node_modules` and `AI5R-STUDIO/osa-web/node_modules` exist on disk but are excluded by a separate, nested `AI5R-STUDIO/dashboard/.gitignore`, not the root one. Adding it at the root protects any *future* JS-based product or tool from the same accidental-commit risk without relying on every new JS subtree remembering to add its own nested `.gitignore`. | Direct inspection this mission (`find AI5R-STUDIO -iname node_modules`, `AI5R-STUDIO/dashboard/.gitignore` confirmed present and already handling that specific case). |

---

## What This Recommendation Deliberately Does NOT Cover

- **`claude_desktop_config.json.bak.json` specifically** is covered by the general `*.bak.*` pattern above — no separate, filename-specific entry is needed or recommended.
- **`RepositoryPack/`** is not recommended for `.gitignore`. Per `REPOSITORY_CLEANUP_AUDIT.md` §5, it is real, versioned, deliberate content (an export package), not a generated artifact — its disposition (commit vs. keep uncommitted vs. distribute separately) is a content decision for the Chief Architect, not a `.gitignore` matter.
- **The empty `BOOTSTRAP/`-family stub files** (`BOOTSTRAP/{CHANGELOG,CURRENT_STATE,ROADMAP,NEXT_ACTION,SESSION}.md` and their mirrored copies) are not recommended for `.gitignore` — they are empty, tracked-or-trackable files, not a class of regenerable artifact; their disposition is a file-management decision (§6 of `EOPS-003-Repository-Hygiene-Report.md`), not a pattern-matching one.

---

This document proposes changes only. `.gitignore` itself has not been edited. Applying these recommendations requires separate, explicit approval, and touches a config file — treat it with the same care as any other approved change once authorized.
