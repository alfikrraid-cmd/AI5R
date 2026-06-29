# AI5R Repository Governance

Version: 1.0.0
Status: DRAFT

---

# Mission

Define repository rules for AI5R development, cleanup, branching, review, and merge.

---

# Branch Strategy

## main

Production branch.

Rules:

- Must always be stable.
- No direct experimental changes.
- Receives changes only through reviewed merge.

## develop

Daily development branch.

Rules:

- Used for integration before production.
- Can receive approved feature branches.
- Must remain runnable.

## feature/xxx

One sprint, one mission branch.

Examples:

```text
feature/repository-cleanup
feature/developer-factory
feature/book-factory
feature/osa-runtime-core

Rules:

Every sprint must use a dedicated feature branch.
Feature branches must have a mission ID.
Feature branches must produce reviewable deliverables.
Repository Cleanup Rule

No cleanup directly on main.

All cleanup must follow:

Audit
↓
Inventory
↓
Migration Matrix
↓
Cleanup Checklist
↓
Execution
↓
Validation
↓
Review
↓
Merge
Folder Naming Rule

Official top-level folders must use uppercase naming.

Examples:

BOOTSTRAP
CONSTITUTION
REGISTRY
SYSTEM
FACTORIES
ARCHITECTURE

Legacy lowercase folders must not be deleted without migration review.

Commit Rule

Every commit must describe the mission and action.

Example:

git commit -m "AI5R-DEV-MISSION-010 add repository governance"
Pull Request Rule

Every pull request must include:

Mission ID
Summary
Files changed
Risk level
Validation steps
Merge recommendation
Review Rule

No branch may be merged until:

Git status is clean
Migration checklist is complete
No accidental deletion is detected
Reviewer approves
