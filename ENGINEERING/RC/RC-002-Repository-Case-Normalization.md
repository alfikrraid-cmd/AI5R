# RC-002 — Repository Case Normalization

Status: VERIFIED DEFECT — NO IMPLEMENTATION APPROVED
Type: Root Cause Record
Related: `REGISTRY/REPORTS/CLEANUP_REPORT.md`, `REGISTRY/MIGRATIONS/MIGRATION_MATRIX.md`, `REGISTRY/MIGRATIONS/CLEANUP_CHECKLIST.md`

---

## Summary

The repository's `HEAD` commit contains two top-level directory trees, `REGISTRY/` and `registry/`, that differ only in letter case. Git tracks them as distinct objects. On case-insensitive filesystems (the default on Windows and macOS) these two paths collide during checkout, so only one of the two trees can be materialized in the working directory at a time. The outcome is non-deterministic across clones, platforms, and checkout order.

---

## Evidence

Commands used (read-only, no working-tree changes):

```text
git config core.ignorecase
→ true
```

```text
git cat-file -p HEAD^{tree}
→
040000 tree 6602d34465f3a5945fd2dedc09a897d332cd12a0  REGISTRY
040000 tree 29b5e675e06766ab891f16f05b8fbaba0e3392e7  registry
```

Two separate tree objects, two separate SHAs, both parented directly under the same commit. This is a property of the git object graph, not a filesystem artifact or a stale working copy.

Contents of each tree differ:

```text
git ls-tree -r HEAD --name-only | grep -i "^registry/"
→
REGISTRY/INVENTORY/REPOSITORY_INVENTORY.md
REGISTRY/MIGRATIONS/CLEANUP_CHECKLIST.md
REGISTRY/MIGRATIONS/MIGRATION_MATRIX.md
REGISTRY/REPORTS/CLEANUP_REPORT.md
REGISTRY/WORKFLOWS/...
registry/BOOTSTRAP/CURRENT_STATE.md
registry/BOOTSTRAP/LOAD.md
registry/BOOTSTRAP/ROADMAP.md
registry/BOOTSTRAP/SESSION.md
registry/CONTITUTION/...        (typo'd, 12 files)
registry/SYSTEM/...              (dependency_graph.json, module_schema.json,
                                   registry.json, runtime.json,
                                   system_manifest.json, version.json,
                                   SYSTEM_PROMPT.md)
registry/readme2
registry/test/TEST-ART-0003.json
registry/workflow/...
```

`REGISTRY/` (uppercase) holds the current platform registry structure introduced under AI5R-DEV-MISSION-010 (`INVENTORY`, `MIGRATIONS`, `REPORTS`, `WORKFLOWS`).
`registry/` (lowercase) holds the pre-existing legacy registry, including a misspelled `CONTITUTION/` directory, a duplicate `SYSTEM/` set of manifests, a duplicate `workflow/` tree, and misc. (`readme2`, `test/`).

The working directory currently only shows the uppercase `REGISTRY/` tree; the lowercase `registry/` tree is present in the git object database but is not independently visible on this checkout's (case-insensitive) filesystem.

---

## Root Cause

1. The repository was originally bootstrapped with a lowercase `registry/` tree (visible in early commit history — `registry/BOOTSTRAP`, `registry/CONTITUTION`, `registry/SYSTEM`, `registry/workflow`, `registry/test`).
2. AI5R-DEV-MISSION-010 ("Repository Cleanup & Platform Registry") introduced a new, standard-cased `REGISTRY/` tree alongside it, per `ARCHITECTURE/REPOSITORY_GOVERNANCE.md`'s folder-naming rule ("official top-level folders must use uppercase naming").
3. Per the mission's own audit (`REGISTRY/REPORTS/CLEANUP_REPORT.md`) and migration matrix (`REGISTRY/MIGRATIONS/MIGRATION_MATRIX.md`), the CTO decision at the time was explicitly to **not** delete or move the legacy lowercase folder immediately, to avoid compounding an active merge conflict, and to migrate content only after review.
4. The migration was partially executed (`CONSTITUTION/`, `REGISTRY/WORKFLOWS/` copied) and the containing PR (#1, commit `92fa68f`) was merged into `main` while `REGISTRY/MIGRATIONS/CLEANUP_CHECKLIST.md` still shows incomplete items (System deferred, Test pending review, Legacy removal deferred to PR #2, all Validation/Merge items unchecked).
5. Net effect: both trees now co-exist permanently in `main`'s history and working tree definition, with no `.gitignore` or repository setting to prevent or flag the case collision, and no enforcement in CI (none observed) to catch it before merge.

---

## Affected Platforms

| Platform | `core.ignorecase` default | Behavior |
|---|---|---|
| Windows | `true` | Collision — only one of `REGISTRY/`/`registry/` materializes in the working tree; determinism not verified across git versions/checkout order |
| macOS (default APFS, case-insensitive) | `true` | Same collision as Windows |
| macOS (case-sensitive APFS variant) | `false` (typically) | No collision — both directories materialize side by side |
| Linux (ext4, most CI runners) | `false` | No collision — both directories materialize side by side, fully visible |

This means the defect is **platform-dependent**: contributors and CI on Linux currently see both trees explicitly (which may itself cause confusion, since two "registries" appear side by side), while contributors on Windows/macOS silently lose visibility into one of them. Behavior has not been verified across different git client versions or partial-clone/sparse-checkout configurations.

---

## Risks

- **Silent data loss on checkout**: whichever tree does not materialize is effectively invisible to a contributor working locally, even though it remains fully present in git history and can resurface unexpectedly (e.g., after a `git rm -r --cached` of the visible tree, or a tool that operates case-sensitively against the index).
- **Non-deterministic checkout outcome**: which of `REGISTRY/`/`registry/` wins is dependent on internal git checkout ordering and is not guaranteed stable across git versions or across a clone vs. an in-place case-normalization change.
- **Platform divergence**: the repository behaves differently on Linux CI vs. Windows/macOS developer machines, which can mask this defect in code review (reviewer on Linux sees both trees; a Windows engineer building locally does not).
- **Governance drift**: this is the second known case where the repository's own cleanup governance (`ARCHITECTURE/REPOSITORY_GOVERNANCE.md`) was not fully followed before merge (see also: CLEANUP_CHECKLIST.md merged with unchecked validation items). Any resolution must not repeat that pattern.
- **Downstream tooling risk**: any script, CI job, or packaging step that reads `REGISTRY/` (uppercase) by convention may silently miss legacy content still living only under `registry/`, or vice versa, depending on platform.

---

## Possible Remediation Options (no recommendation)

1. **Case-normalize via git-native rename**: use a two-step commit (rename to a temporary distinct name, then rename to final uppercase name) to force git to record an explicit rename rather than a no-op case change, then delete the now-empty legacy tree. Requires content review/merge of any legacy-only files first (per MIGRATION_MATRIX.md's own "no deletion, no overwrite" rule).
2. **Complete the deferred MISSION-010 migration**: finish copying/reviewing the remaining legacy content (`registry/SYSTEM`, `registry/test`, `registry/readme2`) into their mapped `REGISTRY/` locations per `MIGRATION_MATRIX.md`, then remove `registry/` entirely in a dedicated, reviewed PR (this was already planned as "PR #2" in `CLEANUP_CHECKLIST.md`).
3. **Enforce `core.ignorecase=false` repo-wide via `.gitattributes`/CI check**: add a CI lint step that fails the build if two paths differing only by case exist in the tree, preventing recurrence without yet resolving the current instance.
4. **Do nothing yet, document and monitor**: leave both trees in place (current state), rely on this RC document and CI/CD platform awareness, and revisit as part of a dedicated Work Order once repository policy work is scheduled (consistent with the CTO's standing decision that "Repository Policy will be implemented later").

No option above has been selected or recommended. Selection is an architectural decision reserved for the CTO / an approved Work Order.

---

## Verification Procedure

Reproducible, read-only steps to confirm this defect on any clone:

```bash
# 1. Confirm case-insensitivity setting (Windows/macOS default = true)
git config core.ignorecase

# 2. List root tree entries as recorded by git (not the filesystem)
git cat-file -p HEAD^{tree}
# Expect: both "REGISTRY" and "registry" listed as separate tree objects with different SHAs

# 3. Enumerate full contents of each tree independently
git ls-tree -r HEAD --name-only | grep "^REGISTRY/"
git ls-tree -r HEAD --name-only | grep "^registry/"
# Expect: differing file listings, confirming these are not the same tree under two names

# 4. Confirm working-tree visibility gap on a case-insensitive filesystem
ls -la ./registry 2>&1   # or: find . -maxdepth 1 -iname registry
# On Windows/macOS (case-insensitive): only one of the two case variants is visible/listed
# On Linux (case-sensitive): both "REGISTRY" and "registry" are visible as separate directories
```

No step above mutates the repository. This procedure can be re-run at any time to re-confirm the defect state before any remediation is scheduled.
