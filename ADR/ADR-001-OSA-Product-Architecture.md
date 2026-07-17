# ADR-001 — OSA Product Architecture

## Status

Proposed

---

## Decision

1. **Business View:** AI5R is the manufacturer (Digital Factory). **OSA is the flagship product/platform** customers request and receive — not Finance, HR, CRM, or any single business capability. Those capabilities are assembled *into* a customer's OSA instance, not sold as separate top-level products.
2. **Engineering View:** `AI5R Digital Factory (Manufacturing Foundation, frozen) → OSA Factory/Runtime (AI5R-SDK/OSA) → Product Runtime (AI5R-SDK/PRODUCT_RUNTIME) → Products (PRODUCTS/*)` — using only components that already exist in the repository.
3. **Product Definition:** a Product is a named, versioned Enterprise Object, composed of declared domains, that has passed through the canonical `Specification → Factory → Artifact → Registry → Runtime → Operation → Evolution` pipeline and is registered under `PRODUCTS/`.
4. **OSA Definition:** **both** — OSA is the engineering-level Factory-and-Runtime (per its own self-declaration and code), and simultaneously the business-level flagship product customers perceive and request. These are not in tension; they are the same system described to two different audiences.
5. **Subsystem Definition:** Finance, HR, CRM, Inventory, Maintenance, Marketing, Procurement, and Project should be **(B) Subsystems/capabilities assembled inside a Product built by OSA — not (A) standalone Products.**
6. **Customer Experience:** a customer requests an outcome (industry, problem, goal), not a component. OSA's intake/blueprint process assembles the needed subsystems into one delivered, named product for them.
7. **AI Workforce:** **lives inside OSA.** It is not a consumer of OSA and not a layer above it — it is implemented as OSA's own orchestration modules.

---

## Context

Three prior, read-only investigations inform this decision, all performed against this repository and cited by file path below — no new discovery was performed for this ADR, per instruction:

- **MWO-OSA-001 (OSA Architecture Review):** established that `AI5R-SDK/OSA` is a real, 33-module, self-contained package (`OSA SYSTEM FACTORY`, `status="FROZEN"`, `version="1.0.0"` per `AI5R-SDK/OSA/RELEASE/osa_release.py`), with zero code coupling to `PRODUCTS/LTSA-BRAIN` in either direction, and that the "osa" substring found inside LTSA-BRAIN's test scripts refers only to the unrelated external hosting domain `n8n.osa-system.com`.
- **MWO-OSA-002 (OSA Product Integration Architecture Review):** established the full intended pipeline (`ARCHITECTURE/AI5R-ARCHITECTURE-SPEC-v2.0.md`'s Manufacturing Foundation → `ARCHITECTURE/REPOSITORY_ARCHITECTURE.md`'s `FACTORIES/OSA Factory` → `AI5R-SDK/PRODUCT_ENGINE`'s canonical 7-stage pipeline → `AI5R-SDK/PRODUCT_RUNTIME` → `AI5R-SDK/OSA`'s runtime modules), and established as fact that this pipeline has **never executed for a real product** — no `product_artifact.json` or `runtime_state.json` exists anywhere in the repository outside each package's own test suite, for LTSA-BRAIN or any other product.
- Both reviews confirmed `PRODUCTS/LTSA-BRAIN` runs entirely on n8n + PostgreSQL, verified at the database level in MWO-P-006, with zero architectural relationship to OSA today.

---

## Reason

**Why OSA is the flagship product, not Finance/HR/CRM individually:** `AI5R-SDK/OSA/GATEWAY/INTAKE/opportunity_intake.py`'s `OpportunityIntakeEngine.analyze()` takes a customer-facing `OpportunityRequest` (industry, problem, goal, deployment) and returns an `OpportunityBlueprint` with a single `system_name` (literally `f"{request.industry} AI OS"`) and a list of `agents`. The customer-facing unit of value is the *system*, not any one of its constituent agents/capabilities. `osa_release.py`'s own capability list (`CUSTOMER_INTAKE`, `OPPORTUNITY_DISCOVERY`, ... `DEPLOYMENT_ORCHESTRATION`) is the complete, self-declared shape of what OSA delivers end-to-end — a full system, not a single department function.

**Why Finance/HR/CRM etc. are Subsystems, not Products (Decision Topic 5), reasoned from three converging pieces of evidence:**
1. `OpportunityBlueprint.agents: list[str]` and `ProductSpecification.domains: list[str]` both model these functions as *members of a list assembled into one Product* — never as independently specified, factory-built, registered, and run entities in their own right. Nothing in `PRODUCT_ENGINE`, `PRODUCT_REGISTRY`, or `PRODUCT_RUNTIME` treats a "domain" or "agent" as something that goes through its own copy of the canonical pipeline.
2. Direct precedent already exists in the one real product in this repository: **`PRODUCTS/LTSA-BRAIN`'s own `product.manifest.json` already declares `maintenance` as one of *its own* modules**, not as a sibling product. If "Maintenance" were meant to be a standalone Product, LTSA-BRAIN's own manifest already contradicts that by containing it as a sub-domain.
3. The Enterprise Object Contract (`AI5R-ARCHITECTURE-SPEC-v2.0.md` §4) lists `product`, `capability`, and `component` as *distinct* object types. Business functions like Finance/HR/CRM map far more naturally onto `capability`/`component` — things composed into a Product — than onto `product` itself, which the Digital Thread (§8) defines as what a Factory *outputs* toward a Customer (`Factory → Product → Release → Customer`), not an input assembled inside one.

**Why AI Workforce lives inside OSA:** `CONSTITUTION/00_IDENTITY.md` states AI5R "builds, manufactures, operates, and governs Digital Organizations composed of Digital Employees." That composition is not abstract — it is concretely implemented as `AI5R-SDK/OSA/EMPLOYEE_ORCHESTRATOR`, `OSA/DIGITAL_EMPLOYEE_ORCHESTRATOR`, and `OSA/MULTI_AGENT_COORDINATOR`, all internal OSA modules that `OSA/ORGANIZATION_RUNTIME` calls directly. There is no separate "AI Workforce" package anywhere in `AI5R-SDK` sitting above or beside OSA consuming it as an external service — the orchestration *is* OSA's own runtime.

---

## Consequences

### Positive
- Gives a single, coherent, evidence-derived story for both audiences (Decision Topics 1–2) that a Chief Architect, an engineer, and a customer-facing document can each reference without contradiction.
- Resolves the ambiguity MWO-OSA-002 deliberately left open (Q4/Q9) with a specific, defensible recommendation rather than leaving future work to re-litigate it.
- Confirms no code, rename, or new engine is required to make this decision true — it is already how the existing components are shaped (per MWO-OSA-002 Deliverable 2's component diagram).
- Gives LTSA-BRAIN a clear conceptual home (a Product, in the now-precise sense of Decision Topic 3) without requiring it to be touched.

### Negative
- The pipeline this decision formalizes has never executed for a real product (see Context). Adopting this ADR as "the reference for future implementation" commits to an architecture that is currently unproven end-to-end, not merely undocumented.
- Treating OSA as simultaneously "the flagship product" and "the runtime" (Decision Topic 4) requires care in future documentation to avoid the exact kind of internal confusion this whole review chain exists to prevent — the two views must stay explicitly labeled (business vs. engineering), not silently merged.
- This ADR does not by itself resolve whether `PRODUCTS/LTSA-BRAIN` should ever be migrated onto this pipeline (see Migration Strategy) — that remains a separate, future decision.

---

## Supersedes

None.

---

## Deliverable — Business Architecture

```
AI5R (Digital Factory — manufacturer, not customer-facing)
   │
   ▼
OSA (flagship product / platform — what a customer requests and receives)
   │
   ├── Finance        ─┐
   ├── HR               │
   ├── CRM               │  Subsystems / capabilities assembled into
   ├── Inventory          │  ONE delivered, named OSA instance per
   ├── Maintenance        │  customer opportunity (e.g. an "Industrial
   ├── Marketing          │  AI OS" — which is, retroactively, what
   ├── Procurement        │  LTSA-BRAIN already is)
   └── Project          ─┘
```

## Deliverable — Engineering Architecture

```
AI5R Digital Factory  (ARCHITECTURE/AI5R-ARCHITECTURE-SPEC-v2.0.md — Manufacturing
                        Foundation, frozen v1.0, LTS)
   │
   ▼
FACTORIES/ → OSA Factory  (ARCHITECTURE/REPOSITORY_ARCHITECTURE.md)
   │
   ▼
AI5R-SDK/OSA/  ("OSA SYSTEM FACTORY" + its own internal runtime:
                ORGANIZATION_RUNTIME, AUTONOMOUS_ORGANIZATION_RUNTIME,
                RUNTIME_PIPELINE)
   │
   ▼
AI5R-SDK/PRODUCT_RUNTIME/  (bridges a registered Product to OSA's
                            RUNTIME_PIPELINE; the "Runtime" stage of
                            PRODUCT_ENGINE's canonical pipeline)
   │
   ▼
PRODUCTS/*  (built via PRODUCT_ENGINE → PRODUCT_ASSEMBLY → PRODUCT_ARTIFACT
             → PRODUCT_REGISTRY, per the canonical Specification → Factory
             → Artifact → Registry → Runtime → Operation → Evolution pipeline)
```

## Deliverable — Product Hierarchy

```
Product                         (Enterprise Object type "product";
  │                              output of Factory → Product → Release
  │                              → Customer, per the Digital Thread)
  │
  ├── domains[] / agents[]      (ProductSpecification.domains,
  │                              OpportunityBlueprint.agents)
  │     │
  │     ├── Finance (subsystem)
  │     ├── HR (subsystem)
  │     ├── CRM (subsystem)
  │     ├── Maintenance (subsystem — precedent: already a module
  │     │                inside PRODUCTS/LTSA-BRAIN's own manifest)
  │     └── ... (Marketing, Procurement, Project, Inventory)
  │
  └── Example instance: PRODUCTS/LTSA-BRAIN
        (a Product in this precise sense, composed of customer/pump/
         seal/asset/inspection/maintenance domains — though not yet
         built through the canonical pipeline; see Migration Strategy)
```

## Deliverable — Recommended Direction

Adopt Decision Topics 1–7 above as the standing architectural reference. Concretely, this means:

- Future subsystem work (Finance, HR, CRM, etc.) should be scoped and built as **capabilities/domains assembled into a Product**, not as independent top-level Products each getting their own Specification/Factory/Artifact/Registry/Runtime cycle.
- Future OSA development should be understood as simultaneously serving two audiences (business: the product itself; engineering: the factory-and-runtime) and documentation should keep these explicitly labeled rather than conflated.
- `PRODUCTS/LTSA-BRAIN` should continue to be referred to, precisely, as a Product in the sense defined here — without requiring any code change to make that true.

## Deliverable — Migration Strategy (conceptual only — no implementation specified)

This ADR does not authorize or specify implementation. Conceptually, the path from current state (pipeline unproven, LTSA-BRAIN fully bypassing it) to the recommended architecture would need, in order:

1. **Reconcile, at the decision level, whether `AI5R-SDK/OSA` *is* the Architecture Spec v2.0's "Runtime Foundation (RT)" domain**, or a separate effort — this ADR does not resolve that; MWO-OSA-002 Gap Analysis flagged it as still open.
2. **Prove the pipeline once, end-to-end, before onboarding any real product onto it** — today it has never produced a real `product_artifact.json` or `runtime_state.json` for anything. A single, minimal, real goal executed through the full chain would be the first evidence the pipeline works outside its own test suite.
3. **Do not force `PRODUCTS/LTSA-BRAIN` onto this pipeline as a prerequisite.** It is already a working, database-verified Product by the definition in this ADR (Decision Topic 3) without having passed through the pipeline mechanically — the pipeline's job going forward is to be validated against *new* work, not to retroactively re-platform something that already works, unless a separate, explicit decision is made to do so.
4. Only after (2) succeeds for at least one real case should further Products or subsystems be planned against this architecture.

No code, rename, or refactor is implied or authorized by this strategy — it is sequencing guidance for whoever scopes that future work.
