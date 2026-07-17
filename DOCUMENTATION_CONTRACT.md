# Documentation Contract

Status: ACTIVE
Authority: Chief Architect
Part of: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` §18 (Documentation Contract)
Rarely changes.

---

## Golden Rule

Documentation is part of the implementation.

Implementation is NOT complete until project documentation has been updated.

A Completion Report alone is NOT sufficient. Engineering Audit must verify documentation consistency before Commit.

---

## Mandatory Documentation

Eight files, at the project root, reused if already present, created only if missing, never duplicated elsewhere:

| File | Purpose | Update cadence |
|---|---|---|
| `CLAUDE.md` | AI identity, Engineering rules, Golden Rules, Working Agreement, Definition of Done | Rarely changes |
| `CURRENT_STATE.md` | Current Product, Current Phase, Current Branch, Current MWO, Last Commit, Next Objective | After every completed MWO |
| `CHANGELOG.md` | Implementation changes only | After every completed MWO |
| `PROJECT_HISTORY.md` | Major milestones only | Whenever a milestone is completed |
| `ROADMAP.md` | Current implementation roadmap | Only when the roadmap changes |
| `MEMORY.md` | Frozen engineering decisions | Only when a new decision becomes permanent |
| `TECHNICAL_DEBT.md` | Architectural debt, known issues, RCA findings, deferred work | Whenever new technical debt is identified |
| `DOCUMENTATION_CONTRACT.md` | This file — defines documentation policy | Rarely changes |

---

## Engineering Workflow (mandatory)

```
Research
    ↓
Architecture Validation
    ↓
Implementation
    ↓
Structural Validation
    ↓
Runtime Validation
    ↓
Documentation Update
    ↓
Completion Report
    ↓
Engineering Audit
    ↓
Commit Recommendation
    ↓
Commit
    ↓
Release
```

---

## Documentation Update Rules

- Whenever an MWO is completed, automatically determine which documentation files must be updated. Do not ask the user which files apply — determine it from the MWO's own scope and deliverables.
- Update only the affected files. Do not rewrite files that are unaffected by the completed MWO.
- Extend existing content; never duplicate a file's purpose in a second location.

## Engineering Audit Rule

Engineering Audit must verify documentation consistency against actual repository state (schema, build packs, ADRs) as one of its checks, in addition to everything already in its scope (file grouping, duplicate detection, architecture compliance, BUILD-PACK consistency, Runtime/Registry/Product boundary, validation execution).

If documentation does not match repository state, the audit must report **FAIL** on that check and stop — a documentation/reality mismatch is treated the same as any other audit FAIL, not a lesser category.

---

## Definition of Done (MWO)

An MWO is complete only when:

- ✓ Implementation complete
- ✓ Validation complete
- ✓ Runtime verification complete (or its absence stated explicitly, with reason — per Engineering Standard §8)
- ✓ Documentation updated
- ✓ Completion Report produced
- ✓ Engineering Audit passed
- ✓ Commit Recommendation produced

Only then may the MWO be considered **Commit Ready**.

---

Established per Chief Architect directive. This file was created as part of a documentation-only mission; no LTSA implementation, Runtime, or BUILD-PACK file was touched in producing it.
