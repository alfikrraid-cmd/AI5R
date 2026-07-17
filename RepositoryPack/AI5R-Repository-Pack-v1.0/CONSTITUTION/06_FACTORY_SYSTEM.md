# 06 — FACTORY SYSTEM
**Document ID:** AI5R-CONST-006  
**Version:** 1.0.0  
**Owner:** B (Founder)  
**Status:** CANONICAL

---

## What Is the Factory System?

The Factory System is AI5R's method of organizing production. It is the operational implementation of the architecture hierarchy (Component → Engine → Factory → Product → Company).

A Factory is not just a workflow. A Factory is a **repeatable production line** that:

- Accepts a mission specification as input
- Executes a defined sequence of engines
- Produces a complete, deployable artifact as output
- Maintains full audit trail, versioning, and rollback capability

---

## The Current Factory: AI5R-DEV-FACTORY-001

### Purpose
Build n8n workflows using AI-assisted engines. The Developer Factory is AI5R's **meta-factory** — it builds the engines and factories that build everything else.

### Mission Execution Flow

```
Mission Input
    ↓
[01] Requirement Engine   →  requirement_spec
    ↓
[02] Architecture Engine  →  architecture_spec
    ↓
[03] Node Builder Engine  →  node_manifest
    ↓
[04] Prompt Engine        →  prompt_library
    ↓
[05] QA Engine            →  qa_report + GO/NO-GO
    ↓
[06] Deployment Engine    →  deployment_report
    ↓
[07] Documentation Engine →  documentation
    ↓
[08] Version Engine       →  version_manifest
    ↓
[09] MCP Engine           →  mcp_config
    ↓
Mission Complete
```

---

## Mission Specification Format

Every Factory run begins with a Mission. A Mission is the unit of work for a Factory.

```json
{
  "mission_id": "DEV-MISSION-{NNN}",
  "mission_name": "Human-readable name",
  "factory": "AI5R-DEV-FACTORY-001",
  "created_at": "ISO8601",
  "created_by": "B",
  "target": "What will be built",
  "requirements": [],
  "constraints": [],
  "success_criteria": [],
  "priority": "HIGH | MEDIUM | LOW",
  "flags": {
    "dry_run": false,
    "abort_on_high_risk": true,
    "human_review_required": false
  }
}
```

---

## Factory Rules

### Rule 1 — One Mission at a Time (v1.0)
In v1.0.0, the Factory runs one mission at a time. Concurrent missions introduce context collision risk. Parallelism is introduced in v1.5 with Redis state management.

### Rule 2 — Context is Cumulative
Each engine receives the full context of all previous engines' outputs. Context grows through the pipeline — it is never reset mid-run.

### Rule 3 — Gates Must Be Respected
The QA Engine's GO/NO-GO gate is binding. A FAIL result halts the pipeline. Only the Founder can manually override with explicit confirmation.

### Rule 4 — Every Run Is Traceable
Every factory execution is logged with: mission_id, timestamp, engine-by-engine status, final result, artifacts produced, and any errors encountered.

### Rule 5 — Rollback Is Mandatory
Before any deployment (Engine 06), a rollback snapshot is taken. No exceptions. A factory that cannot roll back is a factory that cannot be trusted.

---

## Factory Lifecycle

```
DRAFT     →  Mission defined, not started
RUNNING   →  Engines executing
PAUSED    →  Awaiting human review or decision
FAILED    →  Engine returned FAIL, pipeline halted
COMPLETE  →  All engines passed, artifacts deployed
ROLLED_BACK → Deployment reversed via Version Engine
```

---

## Planned Factories

| Factory ID | Name | Status | Purpose |
|---|---|---|---|
| AI5R-DEV-FACTORY-001 | Developer Factory | ACTIVE | Build n8n workflows |
| AI5R-BOOK-FACTORY-001 | Book Factory | PLANNED | Generate ebooks and content products |
| AI5R-WEB-FACTORY-001 | Web Factory | PLANNED | Build landing pages and web products |
| AI5R-DATA-FACTORY-001 | Data Factory | PLANNED | ETL, analytics, reporting |
| AI5R-SALES-FACTORY-001 | Sales Factory | PLANNED | Lead generation and conversion systems |

---

## Factory Graduation Criteria

A Factory graduates from PLANNED to ACTIVE when:

1. All engines are defined and have approved specifications
2. At least one Mission has been run end-to-end in test mode
3. Rollback has been tested and verified
4. Documentation Engine has produced complete documentation
5. Founder has signed off on first production deployment

---

## Context Object Reference

The context object grows through the pipeline:

```json
{
  "mission_id": "DEV-MISSION-001",
  "factory": "AI5R-DEV-FACTORY-001",
  "status": "RUNNING",
  "current_engine": "05-qa",
  "started_at": "2026-06-28T09:00:00Z",
  "artifacts": {
    "requirement_spec": {},
    "architecture_spec": {},
    "node_manifest": {},
    "prompt_library": {},
    "qa_report": {},
    "deployment_report": {},
    "documentation": {},
    "version_manifest": {},
    "mcp_config": {}
  },
  "errors": [],
  "flags": {
    "human_review_required": false,
    "abort_on_high_risk": true,
    "dry_run": false
  }
}
```
