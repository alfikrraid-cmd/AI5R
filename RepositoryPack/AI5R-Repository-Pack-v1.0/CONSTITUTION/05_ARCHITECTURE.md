# 05 — ARCHITECTURE
**Document ID:** AI5R-CONST-005  
**Version:** 1.0.0  
**Owner:** B (Founder)  
**Status:** CANONICAL

---

## The AI5R Architecture Hierarchy

All systems built by AI5R follow one hierarchy. This is not a preference — it is the structural law of AI5R.

```
Component
    ↓
Engine
    ↓
Factory
    ↓
Product
    ↓
Company
```

**Never reverse this hierarchy.** A Company does not become a Factory. A Product does not become a Component. The direction of abstraction is always upward.

---

## Layer Definitions

### Component
The smallest reusable unit. A single, well-defined function with a clear input and output.

- Has one job
- Is fully testable in isolation
- Has no direct knowledge of the system it belongs to
- Examples: SVG-MAZE-001, PDF-RENDERER-001, TOKEN-COUNTER-001

### Engine
A coordinated set of Components that performs a complete, meaningful workflow step.

- Accepts a defined input contract
- Produces a defined output contract
- Can be called by multiple Factories
- Examples: MAZE-ENGINE-001, REQUIREMENT-ENGINE-001, PROMPT-ENGINE-001

### Factory
A system of Engines that delivers a complete business capability end-to-end.

- Orchestrates multiple Engines in sequence or parallel
- Manages state across the pipeline
- Has versioning and rollback capability
- Examples: AI5R-DEV-FACTORY-001, AI5R-BOOK-FACTORY-001

### Product
A Factory packaged for external use — with UI, API, pricing, and documentation.

- Has a defined user
- Has a revenue model
- Has a support and maintenance plan
- Examples: OSA, Maze Generator SaaS, AI5R Developer OS

### Company
The entity that owns and operates multiple Products.

- AI5R is the only Company in this hierarchy
- AI5R owns all Products
- AI5R is built by its own Factories

---

## Naming Convention (Mandatory)

| Layer | Format | Example |
|---|---|---|
| Factory | `AI5R-{DOMAIN}-FACTORY-{NNN}` | `AI5R-DEV-FACTORY-001` |
| Engine | `{DOMAIN}-ENGINE-{NNN}` | `MAZE-ENGINE-001` |
| Component | `{FUNCTION}-{NNN}` | `SVG-MAZE-001` |
| Template | `TPL-{TYPE}-{NNN}` | `TPL-A4-001` |
| Workflow | `{DOMAIN}-WORKFLOW-{NNN}` | `BOOK-WORKFLOW-001` |
| Mission | `DEV-MISSION-{NNN}` | `DEV-MISSION-001` |

Every name must be:
- Uppercase
- Hyphen-separated
- Globally unique within AI5R
- Registered in the Component Registry before use

---

## Component Registry (Mandatory)

Every component, engine, and factory must be registered with:

```json
{
  "id": "MAZE-ENGINE-001",
  "name": "Maze Engine",
  "version": "1.0.0",
  "layer": "Engine",
  "owner": "AI5R",
  "status": "ACTIVE",
  "input_contract": "maze_request",
  "output_contract": "maze_output",
  "dependencies": ["SVG-MAZE-001", "PATHFINDER-001"],
  "factory": "AI5R-DEV-FACTORY-001",
  "created": "2026-06-28",
  "last_modified": "2026-06-28"
}
```

---

## Architecture Principles

### Principle 1 — Contracts are Sacred
Every interface between components must be explicitly defined. A contract change requires a version bump. Breaking changes require a major version increment.

### Principle 2 — Stateless Components, Stateful Engines
Components must be stateless — same input always produces same output. Engines may manage state, but must pass state explicitly, never through side effects.

### Principle 3 — Fail Loud, Recover Gracefully
Components fail with explicit error codes. Engines catch errors and decide: retry, fallback, or escalate. Factories log all failures and maintain a rollback path.

### Principle 4 — One Direction of Data
Data flows down the hierarchy: Factory → Engine → Component. A Component never calls an Engine. An Engine never calls a Factory. Circular dependencies are architectural violations.

### Principle 5 — Version Everything
Every deployed artifact has a semantic version. No "latest" in production. No unversioned releases. The Version Engine is the single source of truth.

### Principle 6 — Design for 10x
Every architecture decision must consider: what happens when this runs at 10x the current volume? If the answer is "it breaks," that must be documented and a path to fix it defined.

---

## The Current System Map

```
AI5R (Company)
│
├── OSA — Opportunity System Architecture (Product)
│   ├── AI5R-DEV-FACTORY-001 (Factory)
│   │   ├── Requirement Engine (Engine 01)
│   │   ├── Architecture Engine (Engine 02)
│   │   ├── Node Builder Engine (Engine 03)
│   │   ├── Prompt Engine (Engine 04)
│   │   ├── QA Engine (Engine 05)
│   │   ├── Deployment Engine (Engine 06)
│   │   ├── Documentation Engine (Engine 07)
│   │   ├── Version Engine (Engine 08)
│   │   └── MCP Engine (Engine 09)
│   │
│   └── [Future Factories]
│
├── Maze Engine v2.0.0 (Product — in development)
│   └── MAZE-ENGINE-001 (Engine)
│       ├── Algorithm Selector (Component)
│       ├── Grid Generator (Component)
│       ├── Pathfinder (Component)
│       └── SVG Renderer (Component)
│
└── [Future Products]
```
