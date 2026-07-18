###############################################################################
# Engineering Practice
###############################################################################

ID            : EP-005
Title         : MWO Lifecycle
Status        : Approved
Version       : 1.0
Owner         : Engineering
Created       : 2026-07-18
Last Updated  : 2026-07-18

###############################################################################

# Purpose

This Engineering Practice defines the official Manufacturing Work Order (MWO)
lifecycle for AI5R, from the business need that originates an MWO through to
its merge into the primary branch.

It exists so every practitioner can see the full path of an MWO in one place,
without re-deriving it from the governing constitution and standard documents
on every occasion.

---

# Scope

This practice applies to every Manufacturing Work Order executed inside the
AI5R Engineering Organization, regardless of product or repository.

It does not replace the canonical sources it is built from:

- `CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md` — chain of command,
  approval authority, and engineering ethics.
- `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` §4 (MWO Lifecycle) and §5
  (Work Package Lifecycle) — the canonical stage definitions.
- `DOCUMENTATION_CONTRACT.md` — the mandatory documentation workflow and
  Definition of Done.

Where this practice and a canonical source differ, the canonical source
governs, per the Blueprint → ADR → Engineering Standard → MWO → Source Code
conformance direction.

---

# Principles

- An MWO always originates from a real business need. No MWO is drafted
  without one.
- The Chief Architect owns MWO Approval, Commit Approval, Push Approval, and
  Release Approval. Claude never assumes any of these.
- Every stage below is a separate, explicit gate. Passing one stage never
  implies approval of the next.
- One MWO produces one commit.
- Discipline over initiative applies across the full lifecycle: work outside
  the active MWO's stated scope is documented and recommended, never
  implemented in place.

---

# Workflow

The MWO lifecycle proceeds through the following stages, in order:

1. **Business Need** — a real product or platform need is identified. This is
   the origin of every MWO; no MWO is invented without one.
2. **MWO Draft** — the MWO is drafted from that business need and from prior
   audit/evidence, never invented from scratch.
3. **Chief Architect Review** — the draft is reviewed, with as many revision
   rounds as the draft's ambiguity requires. Revisions are incorporated into
   the same document, not a new one.
4. **Approval** — explicit, named approval before any implementation begins.
5. **Implementation** — executed per the Work Package Lifecycle (Standard
   §5): implement → validate (structural) → report → stop → wait for
   approval, for each work package.
6. **Validation** — Structural Validation is always performed; Runtime
   Verification is performed or its absence is stated explicitly, with
   reason (Standard §8).
7. **Documentation Update** — the mandatory documentation files affected by
   the implementation are updated, per `DOCUMENTATION_CONTRACT.md`.
8. **Completion Report** — produced once every work package and the
   Documentation Update are complete.
9. **Engineering Audit** — verifies repository consistency and that
   documentation matches actual repository state. A documentation/reality
   mismatch is a FAIL, the same severity as any other audit FAIL.
10. **Commit Recommendation** — states the recommended atomic commit
    grouping, produced only after the Engineering Audit passes.
11. **Commit Approval and Commit** — separate, explicit approval, requested
    and granted, never assumed.
12. **Push Approval and Push** — separate again from Commit Approval,
    requested and granted independently.
13. **Merge** — the branch is merged into `main` only once it meets the
    Merge Policy defined in EP-003 Branching Strategy, and only with
    explicit Chief Architect merge approval.

---

# Engineering Rules

1. No MWO may be drafted without an identifiable business need.
2. Implementation may not begin without explicit Chief Architect approval of
   the governing MWO.
3. One MWO produces one commit.
4. Commit, Push, and Merge each require their own separate, explicit
   approval. None may be assumed from the approval of another.
5. Documentation Update, Completion Report, Engineering Audit, and Commit
   Recommendation may never be skipped or merged into a single step.
6. A branch may not be merged unless it satisfies EP-003's Merge Policy.
7. Work discovered outside the active MWO's scope, at any stage, must be
   documented and recommended, not implemented.
8. Never fabricate or imply a validation, audit, or verification result that
   did not occur.

---

# Completion Criteria

An MWO's lifecycle is complete only when, per the Definition of Done in
`DOCUMENTATION_CONTRACT.md`:

- Implementation complete.
- Validation complete.
- Runtime verification complete, or its absence stated explicitly with
  reason.
- Documentation updated.
- Completion Report produced.
- Engineering Audit passed.
- Commit Recommendation produced.

And, to close the lifecycle this practice defines through Merge:

- Commit approved and performed.
- Push approved and performed.
- Branch merged into `main` under EP-003's Merge Policy.

Only then is the MWO fully closed.

---

# Out of Scope

This practice does not define:

- The internal structure or required sections of an MWO document.
- Branching and naming conventions — see EP-003 Branching Strategy.
- Claude Code session mechanics — see EP-004 Claude Code Workflow.
- Release or deployment procedures that occur after Merge.
- Code review mechanics or commit message formatting — reserved for future
  Engineering Practices.

---

# Summary

The MWO Lifecycle exists to make the full path from business need to merged
code explicit and auditable, without collapsing any of its gates. Every
stage from Business Need through Merge is a separate checkpoint owned by the
Chief Architect; Claude's role is to execute each stage with evidence, stop
at every gate, and wait for approval before proceeding to the next.
