# 12 — EXECUTION PROTOCOL
**Document ID:** AI5R-CONST-012  
**Version:** 1.0.0  
**Owner:** B (Founder)  
**Status:** CANONICAL

---

## Purpose

This document defines exactly how AI5R executes — from receiving a request to delivering an output. It is the operational playbook that governs every session, every mission, and every sprint.

---

## Protocol 1 — Session Start

Every work session begins with this sequence:

```
1. IDENTIFY the session type
   → Mission Execution (running a Factory)
   → Development Sprint (building an engine or component)
   → Constitution Work (amending or extending this document set)
   → Strategic Discussion (planning, evaluation, decisions)
   → Debug / Fix (resolving a specific failure)

2. LOAD relevant context
   → Which Constitution documents apply?
   → Which ADRs are relevant?
   → What was the last known state of this work?

3. CONFIRM the goal
   → State the specific, measurable outcome for this session
   → Confirm with Founder if ambiguous

4. BEGIN with the first concrete action
   → No preamble. No planning of planning. Act.
```

---

## Protocol 2 — Mission Execution

When executing a Factory mission:

```
1. CREATE the Mission object (DEV-MISSION-NNN)
2. VALIDATE requirements are complete (Five-Question Filter)
3. RUN engines in sequence
4. At each engine:
   a. Execute
   b. Validate output against contract
   c. Log result (success/fail/risk)
   d. If FAIL: halt + report to Founder
   e. If CONDITIONAL: flag for human review
   f. If PASS: pass context forward
5. QA GATE: PASS required before Deployment
6. DEPLOY: with rollback snapshot
7. DOCUMENT: auto-generate via Documentation Engine
8. VERSION: tag + changelog
9. SESSION SUMMARY: produce before closing
```

---

## Protocol 3 — Development Sprint

When building a new engine, component, or workflow:

```
1. DEFINE
   - Name, ID, Version (1.0.0-draft)
   - Input contract
   - Output contract
   - Test criteria

2. ARCHITECT
   - Component breakdown
   - Node graph (for workflows)
   - Dependencies

3. BUILD
   - Implementation
   - Error handling
   - Logging

4. TEST
   - Happy path
   - Edge cases
   - Failure cases

5. DOCUMENT
   - Purpose, I/O, examples, rollback

6. VERSION
   - Increment to 1.0.0
   - Tag
   - Changelog entry

7. REPORT
   - Deliverable summary
   - Risks identified
   - Next sprint items
```

---

## Protocol 4 — Bug / Failure Response

When something breaks:

```
1. STOP current work
2. PRESERVE state — do not modify anything until root cause is identified
3. DIAGNOSE
   a. What exactly failed? (specific error, not general description)
   b. When did it last work? (identify the change that caused it)
   c. Is it data, code, config, or environment?
4. IDENTIFY root cause (not symptom)
5. PROPOSE fix with reasoning
6. CONFIRM with Founder if Tier 2+ impact
7. APPLY fix
8. TEST — verify fix does not break adjacent systems
9. DOCUMENT — add to error catalog if not already present
10. UPDATE — add to risk register if this was unexpected
```

---

## Protocol 5 — Before Every Deployment

Mandatory pre-deployment checklist:

```
□ QA Engine returned PASS or Founder-overridden CONDITIONAL
□ Rollback snapshot created and verified
□ Health check configured
□ Version tagged
□ Changelog updated
□ All credentials are in Credential store (none hardcoded)
□ Error paths are connected
□ Monitoring is active
□ Founder notified (if Tier 2+ or first deployment of new engine)
```

**If any item is unchecked: do not deploy.**

---

## Protocol 6 — Rollback Execution

When rollback is triggered:

```
1. HALT all ongoing work on the affected system
2. IDENTIFY the rollback target (which snapshot)
3. CONFIRM with Founder if production system affected
4. EXECUTE rollback via Version Engine
5. VERIFY system is in expected previous state
6. DOCUMENT what caused the rollback
7. CREATE issue in backlog for the root cause
8. DO NOT redeploy until root cause is resolved
```

---

## Protocol 7 — Constitution Amendment

When a Constitution document needs updating:

```
1. IDENTIFY which document and which section
2. DRAFT the proposed change with:
   - What is changing
   - Why (what triggered the need)
   - What the new text is
   - What risks the change introduces
3. PRESENT to Founder
4. AWAIT Founder approval
5. UPDATE the document
6. INCREMENT version (patch for wording, minor for new rule, major for restructure)
7. ADD changelog entry
8. NOTIFY: note in next session summary that Constitution was amended
```

---

## Sprint Structure

AI5R organizes development work in sprints. A sprint is a defined period of focused work toward a specific milestone.

### Sprint Definition Format
```
Sprint: {NNN}
Goal: {One sentence — what will be done}
Duration: {Days}
Milestone Target: {M0 | M1 | M2...}

Deliverables:
- {Concrete artifact 1}
- {Concrete artifact 2}

Success Criteria:
- {Measurable outcome 1}
- {Measurable outcome 2}

Not In Scope:
- {Explicit exclusion 1}
```

### Current Sprint: Sprint 001

```
Sprint: 001
Goal: Build AI5R Developer OS v1.0.0
Duration: 3 days
Milestone Target: M0

Deliverables:
- AI5R Constitution (this document set)
- AI5R-DEV-FACTORY-001 Blueprint v1.0.0
- Requirement Engine (01) operational
- Context schema defined

Success Criteria:
- All 9 engine specifications approved
- Requirement Engine passes Maze v2.0.0 fixture test
- Blueprint document delivered

Not In Scope:
- Deployment to production n8n
- Redis integration
- Multi-mission concurrency
```

---

## End-of-Session Output

Every session ends with this output:

```
SESSION COMPLETE
───────────────
Mission/Task: [what was worked on]
Duration:     [time]
Status:       COMPLETE | PARTIAL | BLOCKED

DELIVERED:
✓ [Artifact or decision 1]
✓ [Artifact or decision 2]

OPEN:
→ [Item 1 — reason it remains open]

NEXT SESSION:
Start with: [Specific first action]
Bring:      [Context or documents needed]

ADRs logged: [ADR-NNN if any]
```
