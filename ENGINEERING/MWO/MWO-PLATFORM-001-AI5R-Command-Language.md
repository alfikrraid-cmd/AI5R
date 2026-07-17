# MWO-PLATFORM-001 — AI5R Command Language

**Status:** FROZEN (WP-000 complete and approved; no implementation work package opened)
**Type:** Platform MWO
**Objective:** Establish ACL-001 as a Platform Artifact — the canonical Operating Language for AI5R.
**Scope:** WP-000 only — the specification. No implementation, no tooling, no code.
**Deliverable:** `AI5R-SDK/PLATFORM/ACL/ACL-001-AI5R-Command-Language.md`

**Review Result:** Architecture PASS · Grammar PASS · Intent Model PASS · Target Model PASS · Address Resolution PASS · Platform Independence PASS.

**Governing Principles (as approved, across all review rounds):**
1. ACL is a Platform Artifact. Type: Canonical Operating Language.
2. ACL expresses intent. UMR decides execution.
3. "Manufacture" replaces "Implement" as the primary execution command; "Implement" is a legacy alias only.
4. First-class commands: Research, Manufacture, Review, Commit, Resume, Load, Status.
5. Four Operating Modes: Research, Manufacture, Review, Commit.
6. ACL Principles: intent over implementation; execution belongs to UMR; one command, one intent; no runtime logic; no implementation logic.
7. ACL is independent from UMR — ACL describes the language, UMR executes it.
8. Every ACL command maps to an existing AI5R Engineering Workflow phase — no second workflow introduced.
9. Human-first, machine-readable second. Grammar: Sentence = Verb + Target + Optional Context. Consumers: Humans, AI Workers, AI5R Runtime.
10. Target is classified into a Canonical Target Space: Artifact, Factory Pack, Platform, Product, Capability, Worker, Knowledge, MWO.
11. ACL names Target; UMR resolves Target.
12. ACL shall never expose implementation details.
13. ACL Evolution Policy: future commands preserve the canonical grammar; backward compatibility is mandatory.

**Placement Note (per this MWO's own closing architectural refinement):** MWO documents remain under `ENGINEERING/MWO/`. Canonical Platform Artifacts do not live under `ENGINEERING/` — they live under `AI5R-SDK/PLATFORM/`. This document (the work) stays here; ACL-001 (the artifact) has moved to `AI5R-SDK/PLATFORM/ACL/`. Under the same rule, `UMR-001-Universal-Manufacturing-Runtime-Specification.md` (a Canonical Platform Runtime artifact, previously misplaced under `ENGINEERING/MWO/`) has been relocated to `AI5R-SDK/PLATFORM/MANUFACTURING/` as part of this MWO's persistence step.

**Next Step:** Persisted. Not committed. Waiting for separate, explicit commit approval.
