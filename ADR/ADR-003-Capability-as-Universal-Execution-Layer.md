# ADR-003 — Capability as Universal Execution Layer

## Status

Proposed

## Context

ADR-002 established that AI5R owns BRAIN as a peer strategic asset, consumed by OSA — not owned by it — through `CapabilityRuntime`'s existing engine-injection point, so that BRAIN remains reusable across every future AI5R product. That decision left one relationship still implicit: what Capability itself is, and why it was the correct seam for OSA to consume BRAIN through in the first place, rather than an OSA-private mechanism.

This ADR formalizes that relationship. It does not redesign anything ADR-001 or ADR-002 established, and it does not introduce a new concept — `CAPABILITY/` already exists in the repository as a real, frozen-specified package (`CP-008`), already the injection point ADR-002's migration strategy names. This ADR states explicitly what was already true of it: Capability is not a product, not part of OSA, not owned by BRAIN, and not owned by Factory. It is a peer strategic asset owned directly by AI5R, exactly as ADR-002 already treats BRAIN.

## Decision

**AI5R owns these strategic platform assets as peers: Knowledge, Capability, BRAIN, Factory, Runtime, Foundation, and Products.** OSA is a product built on AI5R — one consumer among the products this list anticipates, not a peer asset itself.

**BRAIN decides. Capability executes.** This is the governing distinction of this ADR. BRAIN, per ADR-002, is the Enterprise Cognitive Processor — it reasons about what should happen (e.g., "search the internet," "write an email," "create a presentation," "use Photoshop," "deploy an application"). Capability is the universal execution layer that actually performs the action BRAIN decided on. Neither replaces the other: a decision without an execution layer cannot act; an execution layer without a decision layer has nothing directing it.

**Capability is a reusable platform asset owned directly by AI5R.**
- Capability is **not** a product.
- Capability is **not** part of OSA.
- Capability is **not** owned by BRAIN.
- Capability is **not** owned by Factory.

Every AI5R product — OSA today, and any future product (Education OS, Manufacturing OS, Healthcare OS, Robotics OS, DreamPath, or others) — uses Capability the same way every such product may use BRAIN: as a peer asset it consumes, never as something it owns or that is scoped privately to it.

### Dependency Direction

```
Products
    ↓
Capability Runtime
    ↓
Capability
```

This is the only permitted direction. Explicitly **not** permitted:

```
Capability          Capability
    ↓          and      ↓
   OSA               Any Product
```

Capability must never depend on a product, including OSA. A product may depend on Capability. This mirrors, and is structurally consistent with, ADR-002's rule that OSA consumes BRAIN rather than owning it — the same asymmetry applies here: the peer asset never depends downward on the thing consuming it.

### Capability Categories

Capability is organized into the following groups. Each group names a class of executable action Capability performs on behalf of a decision made elsewhere (by BRAIN, by a human, or by any other AI5R product):

**Knowledge** — Search, RAG, Memory, Knowledge Graph, OCR

**Communication** — Email, WhatsApp, Telegram, Slack, Discord

**Productivity** — Documents, Spreadsheet, Presentation, Calendar, Notes

**Development** — Python, Node, Docker, Git, Terminal, Database, API

**Creative** — Photoshop, Illustrator, Canva, Figma, Video, Audio

**Business** — ERP, CRM, Accounting, HRIS, Marketplace

**Browser** — Chrome, Playwright, Selenium, Web Automation

**AI** — LLM, Vision, Speech, Embedding, Reasoning

Each named item in every group above is a Capability implementation — a concrete, invocable unit of business function in the sense already established by `CP-008` and Blueprint Vol. II, Ch.6, not a new kind of object.

---

## Architectural Rules

**Rule-001**
Capability SHALL NEVER depend on any Product.

**Rule-002**
Products MAY consume Capability through Capability Runtime.

**Rule-003**
Capability implementations MUST be reusable.

**Rule-004**
Provider implementations MUST be replaceable without changing Products.

**Rule-005**
Capability SHALL expose stable interfaces.

---

## Rationale

Without a single, AI5R-owned Capability layer, every product would independently build its own integration to every external system it needs — its own email adapter, its own Photoshop adapter, its own CRM adapter, its own browser-automation adapter, repeated once per product. This is precisely the fragmentation pattern the Blueprint (Vol. I, Ch.1–2) identifies as the failure mode of prior generations of enterprise software, recurring one layer down at the integration level if Capability were not a shared, AI5R-owned asset.

**Duplicated integrations and APIs.** Each product re-implementing "send an email" or "search the web" multiplies the surface area that must be built, documented, and kept correct — the same work paid for repeatedly instead of once.

**Duplicated provider adapters.** A Photoshop or CRM provider's API changes over time. Rule-004 (providers must be replaceable without changing Products) means that change is absorbed once, inside Capability, rather than once per product that happens to use Photoshop or a CRM.

**Duplicated authentication.** Credential handling for Slack, Discord, a CRM, or a Git host is a security-sensitive concern best implemented once and reused, not re-derived per product with the attendant risk of inconsistent handling.

**Duplicated maintenance.** A bug fix, rate-limit accommodation, or new provider version lands once, in Capability, and every consuming product benefits immediately — the same Continuous Evolution mechanism ADR-002 already established for BRAIN/Knowledge (Learning improves Knowledge; Knowledge improves Capability) applies symmetrically here: a Capability improved for one product's use strengthens every product's use, exactly as Blueprint Vol. I, Ch.5's Continuous Evolution principle describes for OSA itself, now extended to the execution layer beneath every AI5R product, not only OSA.

A single Capability implementation therefore benefits every AI5R product for the same reason a single OSA benefits every OSA System (Blueprint Vol. I, Ch.6): multiplicity of consumers is not in tension with unity of implementation — it is why the implementation is worth building once, to a high standard, rather than many times to a merely adequate one.

---

## Consequences

### Positive
- Gives Capability an explicit, AI5R-level home consistent with BRAIN's (ADR-002), rather than leaving its ownership implicit or inferable only from where `CAPABILITY/` happens to live in the repository tree.
- Establishes a single dependency direction (Products → Capability Runtime → Capability) that, if honored, prevents any future product from accidentally becoming a hidden dependency of the execution layer every other product also relies on.
- Gives future capability work (new providers within Knowledge, Communication, Productivity, Development, Creative, Business, Browser, or AI groups) a pre-defined home and a pre-defined rule set (Rule-001 through Rule-005) to build against, rather than requiring each addition to re-derive placement.

### Negative
- This ADR is a formalization, not an implementation — none of the eight capability groups above are confirmed built or wired as of this document; their presence here states intent, matching Section 2's normative framing in ADR-002, not current repository state.
- Rule-004's replaceability requirement is not yet verified against any real provider implementation in the repository; enforcing it will be a future MWO's concern, not something this ADR itself proves.

## Alternatives Considered

- **Scope Capability to OSA, as an OSA-internal execution mechanism** — rejected, for the same reason ADR-002 rejected OSA owning BRAIN: it would foreclose reuse by future AI5R products with no relationship to OSA.
- **Let each product build its own execution/integration layer** — rejected; this is the fragmentation pattern the Rationale section describes, and the one the Blueprint's entire premise (Vol. I, Ch.1–2) exists to avoid one layer up.
- **Make Capability a child of BRAIN, since BRAIN is the layer that decides what to execute** — rejected; conflating decision and execution into one owned hierarchy would prevent Capability from being consumed by a product or process that does not go through BRAIN at all (e.g., a human-directed or rules-driven product action), and contradicts the "BRAIN decides, Capability executes" separation this ADR establishes as load-bearing.

## Future Impact

This ADR becomes the canonical reference for any future MWO that adds a Capability provider within the eight named groups, or that wires a product's consumption of Capability through Capability Runtime. Any such MWO must cite Rule-001 through Rule-005, must not introduce a Capability that depends on the product it serves, and must keep provider implementations replaceable per Rule-004. This ADR does not authorize or schedule the implementation of any specific capability group — it defines the architecture such future implementation work must conform to.

## Supersedes

None. This ADR extends ADR-002; it does not revise or replace it.
