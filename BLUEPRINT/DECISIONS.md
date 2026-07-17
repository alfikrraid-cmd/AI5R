# Blueprint Decisions

This document summarizes architecture and product decisions already approved prior to this Blueprint's governance foundation. No decision listed here is new — each is extracted from, and cites, the document in which it was originally approved. Where a decision is expressed both formally (ADR-001) and narratively (Volume I), both sources are cited.

**Status convention:** "Frozen" reflects the Blueprint's own declared Architecture Freeze status (see `STATUS.md`, Blueprint Freeze Status). `ADR-001`'s own internal status field reads "Proposed" and is not modified by this document or by any Blueprint freeze decision — the Blueprint Freeze process governs Blueprint status independently of ADR drafting status. An ADR's internal status field tracks that ADR's own review lifecycle as an architecture-decision artifact; a decision's status *in this document* tracks whether the Blueprint has adopted and frozen it as part of the official reference. The two statuses answer different questions and are not expected to move together — ADR-001 remaining "Proposed" in its own document does not prevent the decisions it records from being "Frozen" here, once the Blueprint itself freezes them.

A decision marked "Frozen" in this document is stable and not to be casually revised, per the freeze policy in `README.md`.

---

### BP-DEC-001

**Decision Statement:** AI5R is a Digital Factory — the manufacturer of OSA — not an ERP company, a single-product vendor, or a consultancy assembling bespoke systems. OSA is the flagship product AI5R manufactures.

**Source:** ADR-001, Decision Topic 1 (Business View); Volume I, Chapter 3 (AI5R Digital Factory)

**Status:** Frozen

**Version:** v1.0

**Notes:** Foundational to every other decision in this document.

---

### BP-DEC-002

**Decision Statement:** The engineering-level architecture is: AI5R Digital Factory (Manufacturing Foundation) → OSA Factory/Runtime → Product Runtime → Products.

**Source:** ADR-001, Decision Topic 2 (Engineering View)

**Status:** Frozen

**Version:** v1.0

**Notes:** Uses only architectural components already established; no new engine or layer was introduced by this decision. Volume II, Chapter 3 elaborates the "OSA Factory/Runtime" stage of this pipeline into three structural components for architectural precision — see BP-DEC-015 (OSA Core) and BP-DEC-016 (OSA Runtime), which formalize that elaboration; Product Runtime remains as defined here.

---

### BP-DEC-003

**Decision Statement:** A Product is a named, versioned Enterprise Object, composed of declared domains, that has passed through the canonical Specification → Factory → Artifact → Registry → Runtime → Operation → Evolution pipeline and is registered as a Product.

**Source:** ADR-001, Decision Topic 3 (Product Definition)

**Status:** Frozen

**Version:** v1.0

**Notes:** This is the precise, technical definition of "Product." Compare BP-DEC-005, which governs what should and should not be modeled as a Product. This decision's 7-stage pipeline (Specification → Factory → Artifact → Registry → Runtime → Operation → Evolution) and Volume II Chapter 2's 5-stage Manufacturing Lifecycle (Specification → Product Manufacturing → Verification → Deployment → Continuous Evolution) are the same lifecycle at two resolutions, not two lifecycles — Chapter 2 includes an explicit stage-by-stage mapping between the two.

---

### BP-DEC-004

**Decision Statement:** OSA is both the engineering-level Factory-and-Runtime and the business-level flagship product customers perceive and request. These are not in tension — they are the same system described to two different audiences.

**Source:** ADR-001, Decision Topic 4 (OSA Definition); Volume I, Chapter 4 (What is OSA?)

**Status:** Frozen

**Version:** v1.0

**Notes:** Volume I's Chapter 4 negative definition ("OSA is not ERP / not CRM / not Accounting Software") is the customer-facing expression of this same decision.

---

### BP-DEC-005

**Decision Statement:** Finance, HR, CRM, Inventory, Maintenance, Marketing, Procurement, and Project should be modeled as Subsystems/capabilities assembled inside a Product built by OSA — not as standalone Products in their own right.

**Source:** ADR-001, Decision Topic 5 (Subsystem Definition); Volume I, Chapter 6 (OSA Systems)

**Status:** Frozen

**Version:** v1.0

**Notes:** Referred to as "OSA Systems" in Volume I's customer-facing language. This is the decision that gives the "Many Systems" principle (BP-DEC-010) its concrete meaning.

---

### BP-DEC-006

**Decision Statement:** A customer requests an outcome (industry, problem, goal) rather than a specific component. OSA's intake and blueprint process assembles the needed Systems into one delivered, named product for that customer.

**Source:** ADR-001, Decision Topic 6 (Customer Experience); Volume I, Chapter 8 (Customer Journey)

**Status:** Frozen

**Version:** v1.0

**Notes:** Volume I, Chapter 8's flow (Business Challenge → Business Discovery → OSA Manufacturing → OSA Deployment → OSA Instance → AI Workforce → Continuous Evolution) is the full, narrative expression of this decision.

---

### BP-DEC-007

**Decision Statement:** AI Workforce lives inside OSA. It is not a separate product consuming OSA as an external service, and not a layer sitting above OSA — it is implemented as OSA's own orchestration.

**Source:** ADR-001, Decision Topic 7 (AI Workforce); Volume I, Chapter 7 (AI Workforce)

**Status:** Frozen

**Version:** v1.0

**Notes:** Governs where future AI Workforce capability is designed and documented — inside the OSA Systems and Product architecture, not as a parallel track.

---

### BP-DEC-008

**Decision Statement:** One Company — OSA is manufactured by a single company with one coherent vision, not a federation of acquired products under a shared brand.

**Source:** Volume I, Chapter 5 (The OSA Philosophy)

**Status:** Frozen

**Version:** v1.0

**Notes:** First of the seven OSA Philosophy principles.

---

### BP-DEC-009

**Decision Statement:** One Product — there is one OSA, not a family of differently-scoped offerings. An enterprise adopts OSA, configured to its needs, not a choice between fundamentally different products.

**Source:** Volume I, Chapter 5 (The OSA Philosophy)

**Status:** Frozen

**Version:** v1.0

**Notes:** Directly supports BP-DEC-001 and BP-DEC-004.

---

### BP-DEC-010

**Decision Statement:** Many Systems — within the one product, OSA is composed of many Systems, each addressing a distinct business function, without that multiplicity fragmenting the product.

**Source:** Volume I, Chapter 5 (The OSA Philosophy); Chapter 6 (OSA Systems)

**Status:** Frozen

**Version:** v1.0

**Notes:** The philosophical basis for BP-DEC-005.

---

### BP-DEC-011

**Decision Statement:** One AI Workforce — every System within OSA is staffed, in part, by the same AI Workforce architecture, not a separate AI feature built independently per System.

**Source:** Volume I, Chapter 5 (The OSA Philosophy)

**Status:** Frozen

**Version:** v1.0

**Notes:** The philosophical basis for BP-DEC-007.

---

### BP-DEC-012

**Decision Statement:** Business First — OSA is designed from business outcomes backward, not from technology capability forward. Capability is added because a business need exists for it, not because the underlying technology permits it.

**Source:** Volume I, Chapter 5 (The OSA Philosophy)

**Status:** Frozen

**Version:** v1.0

**Notes:** Governs prioritization for future volume and capability planning.

---

### BP-DEC-013

**Decision Statement:** Composable Enterprise — the Systems an enterprise runs, and the AI Workforce roles it employs, can be composed and recomposed to match its actual requirements without a new integration project for every change.

**Source:** Volume I, Chapter 5 (The OSA Philosophy)

**Status:** Frozen

**Version:** v1.0

**Notes:** Supports the Industry Examples in Volume I, Chapter 9.

---

### BP-DEC-014

**Decision Statement:** Continuous Evolution — OSA is never delivered as a finished, static artifact. Improvements made for one enterprise strengthen the product every enterprise runs, delivered as ongoing improvement rather than disruptive upgrade projects.

**Source:** Volume I, Chapter 5 (The OSA Philosophy)

**Status:** Frozen

**Version:** v1.0

**Notes:** Governs how future volumes should describe product evolution and versioning for customer-facing instances, as distinct from Blueprint document versioning (see `README.md`, Versioning Policy).

---

### BP-DEC-015

**Decision Statement:** OSA Core is the foundation every OSA Instance shares regardless of which Systems it runs: the Enterprise Object model, the Capability Registry, and the orchestration mechanism through which AI Workforce acts. OSA Core contains no System-specific business logic.

**Source:** Volume II, Chapter 3 (OSA Enterprise Operating System); Chapter 10 (Architecture Rules) — formalizing the "OSA Factory/Runtime" component of ADR-001 Decision Topic 2 / BP-DEC-002 with architectural precision.

**Status:** Frozen

**Version:** v1.0

**Notes:** Added during the Architecture Freeze Review reconciliation pass (MWO-BP-007, Issue C) to close a gap: this component was established and relied upon throughout Volume II but had no corresponding entry in this document.

---

### BP-DEC-016

**Decision Statement:** OSA Runtime is the execution layer built on OSA Core — the mechanism through which a goal is resolved into a capability, directed at the relevant OSA Systems, and carried out against the relevant Enterprise Objects.

**Source:** Volume II, Chapter 3 (OSA Enterprise Operating System) — formalizing the "OSA Factory/Runtime" component of ADR-001 Decision Topic 2 / BP-DEC-002 with architectural precision.

**Status:** Frozen

**Version:** v1.0

**Notes:** Added during the Architecture Freeze Review reconciliation pass (MWO-BP-007, Issue C), for the same reason as BP-DEC-015. Distinct from Product Runtime (BP-DEC-002's existing definition), which applies OSA Runtime to one specific, manufactured instance rather than providing the general execution mechanism itself.

---

### BP-DEC-017

**Decision Statement:** AI Workforce is organized as a six-level hierarchy — CEO AI, Executive AI, Director AI, Manager AI, Specialist AI, Employee AI. Volume I presents the four primary levels (CEO, Director, Manager, Employee) at the resolution appropriate to an executive audience; this is the same hierarchy, not a different one. The six-level structure itself is frozen, on the same basis as OSA Core's layered architecture; staffing — how many instances of each role are composed within a given OSA Instance — is unlimited and evolvable.

**Source:** Volume II, Chapter 7 (AI Workforce Architecture); Chapter 10 (Architecture Rules); reconciled with Volume I, Chapter 7 and Glossary during MWO-BP-007.

**Status:** Frozen

**Version:** v1.0

**Notes:** Added during the Architecture Freeze Review reconciliation pass (MWO-BP-007, Issues A and E) to resolve a genuine inconsistency the review identified: Volume I stated four levels in closed-list form in three separate places (Chapter 7, Chapter 8, Glossary) while Volume II introduced six without cross-referencing the difference. Both volumes have since been updated to state explicitly that these are one hierarchy at two resolutions.
