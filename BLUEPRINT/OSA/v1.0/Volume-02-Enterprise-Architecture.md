# OSA Enterprise Operating System Blueprint

**Version 1.0 — Volume II: Enterprise Architecture**

*Published by AI5R Digital Factory*

---

## Table of Contents

**Preface**

1. Enterprise Architecture Overview
2. AI5R Digital Factory
3. OSA Enterprise Operating System
4. OSA Systems
5. Enterprise Objects
6. Capability Architecture
7. AI Workforce Architecture
8. OSA Instance
9. Runtime Architecture
10. Architecture Rules

**Final Summary**

---

## Preface

Volume I established what OSA is, why it exists, and the philosophy that governs it. Volume II builds on that foundation without revisiting it. Every principle stated in Volume I — One Company, One Product, Many Systems, One AI Workforce, Business First, Composable Enterprise, Continuous Evolution — is treated here as settled, not as a question to be reopened.

This volume exists for a different audience than Volume I. Where Volume I spoke to vision and positioning, Volume II speaks to structure: how OSA is architected, how its parts relate, how it operates, and how it scales. It is written for architects who must design against OSA, engineers who must reason about where new capability belongs, and executives who need to understand the structural logic behind a system they have already decided to trust.

This volume does not describe how OSA is implemented. It describes how OSA is architected — a distinction that matters throughout. Architecture is the stable structure that implementation serves; it does not change with every implementation choice, and this volume does not depend on any particular one.

---

## Chapter 1 — Enterprise Architecture Overview

OSA's architecture is a layered structure, in which each layer exists because the layer beneath it is insufficient on its own to serve an enterprise.

```
AI5R
  │  (the company — manufacturer, not operator)
  ▼
Digital Factory
  │  (the manufacturing discipline AI5R applies to every product)
  ▼
OSA
  │  (the flagship product — the Enterprise Operating System itself)
  ▼
OSA Systems
  │  (the composable functional units OSA is built from)
  ▼
Enterprise Objects
  │  (the shared vocabulary every System reasons about)
  ▼
AI Workforce
  │  (the orchestration layer that acts on Enterprise Objects through Systems)
  ▼
OSA Instance
     (the specific, composed, operating environment a customer runs)
```

**AI5R** sits at the top of this structure as the manufacturer, not a participant in daily operation. It does not run any customer's business; it manufactures the product that does.

**Digital Factory** is the discipline AI5R applies to that manufacturing — a repeatable process rather than a one-off engineering effort, detailed in Chapter 2.

**OSA** is the product that discipline produces: the Enterprise Operating System itself, defined precisely in Chapter 3.

**OSA Systems** are the composable functional units OSA is built from — Finance, HR, Maintenance, and the many others catalogued in Chapter 4. A System is where a specific business function lives.

**Enterprise Objects** are the shared vocabulary every System reasons about — a Customer, an Asset, an Invoice — defined once and understood consistently across every System that touches them, detailed in Chapter 5.

**AI Workforce** is the layer that acts — coordinating Systems, operating on Enterprise Objects, and carrying out the goals an enterprise sets, detailed in Chapter 7.

**OSA Instance** is where all of the above becomes real for a specific enterprise: a particular composition of Systems, staffed by a particular composition of AI Workforce, operating on that enterprise's own Enterprise Objects, detailed in Chapter 8.

Each layer is stable on its own terms even as the layers around it change. New OSA Systems can be introduced without altering OSA itself. New Enterprise Object types can be defined without altering the Systems that already exist. New OSA Instances can be composed without altering any of the architecture that composes them. This stability-through-layering is the architectural property that makes OSA's composability (Volume I, Chapter 5) possible in structural terms, not only in philosophy.

---

## Chapter 2 — AI5R Digital Factory

**Digital Factory philosophy.** A factory does not build one thing once; it builds a defined thing repeatedly, to a consistent standard, with quality that improves as the factory itself matures. AI5R applies this discipline to digital products in general and to OSA specifically. The alternative — treating each deployment as a custom engineering project — is the pattern that produced the fragmentation Volume I identifies as the problem OSA exists to solve. A factory discipline is what prevents OSA from decaying into exactly that pattern as it scales across customers.

**Manufacturing lifecycle.** Every OSA Instance passes through the same production lifecycle, regardless of which enterprise it serves:

```
Specification
     │
     ▼
Product Manufacturing
     │
     ▼
Verification
     │
     ▼
Deployment
     │
     ▼
Continuous Evolution
```

**Specification** captures what a given OSA Instance needs to be — which OSA Systems it requires, which Enterprise Objects it must model, which AI Workforce roles it needs staffed. This is the output of Business Discovery, detailed in Chapter 8.

**Product Manufacturing** produces the instance from that specification — assembling the specified Systems, provisioning the specified Enterprise Object model, and preparing the specified AI Workforce roles into one coherent, ready-to-operate product.

**Verification** confirms the manufactured instance is correct before it reaches an enterprise — that the Systems specified are present, that Enterprise Objects behave as their definitions require, and that AI Workforce roles are properly staffed and connected to the Systems they will orchestrate.

**Deployment** places the verified instance into operation for the enterprise it was manufactured for.

**Continuous Evolution** does not end the lifecycle — it re-enters it. As an enterprise's needs change, or as the OSA product itself improves, the instance moves through Specification, Manufacturing, and Verification again, in smaller and more frequent cycles than the original deployment, without the enterprise experiencing this as a disruptive replacement.

**How AI5R manufactures OSA.** This same lifecycle governs OSA itself, not only the instances built from it. OSA is not manufactured once and then left static — it is a product AI5R continuously specifies, manufactures, verifies, and evolves, exactly as it does for the instances customers run. This is what allows every OSA Instance to benefit from improvements made anywhere in the product, per the Continuous Evolution principle established in Volume I.

**One canonical lifecycle, described at two resolutions.** `DECISIONS.md` (BP-DEC-003) records this same lifecycle at a finer technical resolution, as seven stages: Specification → Factory → Artifact → Registry → Runtime → Operation → Evolution. This is not a second, different lifecycle — it is the same five stages above, described at the resolution a technical decision record requires:

| This chapter (architectural, 5 stages) | `DECISIONS.md` BP-DEC-003 (technical, 7 stages) |
|---|---|
| Specification | Specification |
| Product Manufacturing | Factory, Artifact *(the building and the built output, together)* |
| Verification | *(implicit within Registry — an artifact is only correctly registered once confirmed correct; this chapter names that confirmation as its own stage)* |
| Deployment | Registry, Runtime *(registering the verified instance and beginning its execution, together)* |
| Continuous Evolution | Operation, Evolution *(ongoing operation and the evolution it feeds, together)* |

Two clarifications follow. First, **Verification is not a new stage invented for this chapter** — a manufactured instance has always had to be confirmed correct before an enterprise could rely on it; this chapter simply gives that necessity its own name rather than leaving it implicit inside Registry. Second, **which framing to use depends on the reader**: the five-stage form is the one every other chapter of this volume references, and is the one to use when discussing OSA's architecture; the seven-stage form is the technical decision record's own vocabulary, unchanged, and remains the reference for that document specifically.

---

## Chapter 3 — OSA Enterprise Operating System

**Official engineering definition:** OSA is the Enterprise Operating System manufactured by AI5R — the architected environment in which OSA Systems, Enterprise Objects, and AI Workforce operate as one coherent whole, instantiated per enterprise as an OSA Instance.

This definition rests on three structural components and one lifecycle that runs through them.

**OSA Core** is the foundation every OSA Instance shares, regardless of which Systems it runs: the Enterprise Object model (Chapter 5), the Capability Registry (Chapter 6), and the orchestration mechanism through which AI Workforce acts. OSA Core does not contain any specific System's business logic — it contains the shared structure that makes every System interoperable without custom integration.

**OSA Runtime** is the execution layer built on OSA Core — the mechanism through which a goal becomes action: resolved into a capability, directed at the relevant OSA Systems, and carried out against the relevant Enterprise Objects. OSA Runtime is what makes OSA an *operating* system rather than a static architecture — it is where execution actually happens.

**Product Runtime** governs the operation of one specific, manufactured OSA Instance — bringing that instance's particular composition of Systems, Objects, and Workforce roles into OSA Runtime and keeping it operating as the enterprise's needs evolve. Where OSA Runtime is the general execution mechanism, Product Runtime is what applies that mechanism to a specific, living instance.

**Runtime Lifecycle** is not a fourth structure alongside the three above — it is the process that runs through them: the sequence a goal follows from statement to outcome, architected in full in Chapter 9. OSA Core provides the structure, OSA Runtime provides the execution mechanism, and Product Runtime applies both to a specific instance; the Runtime Lifecycle is what happens, in sequence, once all three structural components are in place.

**Business View and Engineering View.** OSA is described differently to different audiences, deliberately, and both descriptions are correct at once.

To an **executive or a customer**, OSA is a product: the operating environment their enterprise runs on, composed of the Systems they need, staffed by an AI Workforce that works alongside their people. They do not need to reason about Core, Runtime, or Product Runtime to understand what they have — they need to understand what it does for their enterprise, which Volume I addresses directly.

To an **engineer or architect**, OSA is the four-component structure defined above — a Core that provides shared structure, a Runtime that executes, a Product Runtime that operates a specific instance, and a lifecycle that governs how goals move through the system. This is the vocabulary this volume, and every subsequent architectural document, uses.

Neither view supersedes the other. A business decision about which OSA Systems an enterprise needs (Business View) has a direct architectural consequence for how that instance's Product Runtime is composed (Engineering View) — the two views describe the same reality from two vantage points, exactly as Volume I established for OSA as a whole.

---

## Chapter 4 — OSA Systems

An OSA System is a composable functional unit addressing one organizational function, built on OSA Core, exposing its function to the rest of OSA through capabilities (Chapter 6), and operating on Enterprise Objects (Chapter 5) shared with every other System.

OSA is designed so that any function that exists in a real organization can be represented as an OSA System. The following catalogue illustrates the breadth of that design intent, grouped by the organizational domain each System serves. It is representative, not exhaustive — the architecture explicitly does not require this list to be closed (see Architecture Rules, Chapter 10).

| Domain | OSA Systems |
|---|---|
| Executive & Strategy | OSA Executive, OSA Strategy, OSA Analytics |
| Finance | OSA Finance, OSA Accounting, OSA Treasury, OSA Tax |
| People | OSA HR, OSA Recruitment, OSA Learning |
| Commercial | OSA Sales, OSA Marketing, OSA CRM |
| Supply Chain | OSA Procurement, OSA Inventory, OSA Warehouse, OSA Logistics |
| Operations | OSA Manufacturing, OSA Engineering, OSA Maintenance, OSA Project |
| Governance & Risk | OSA Legal, OSA Audit, OSA Compliance, OSA Risk, OSA Security |
| Technology & Knowledge | OSA IT, OSA Knowledge, OSA Research, OSA AI |
| Enterprise Services | OSA Administration, OSA Organizer, OSA Customer Service, OSA Quality |
| Platform Services | OSA Document, OSA Workflow, OSA Notification, OSA Reporting |
| Extensibility | OSA Custom Systems |

Two architectural facts follow from this design intent, and both are load-bearing for everything else in this volume.

**These are examples of organizational systems, not a fixed product catalogue.** OSA is not architected around a specific list of functions any more than an operating system is architected around a specific list of applications. It is architected around the *capacity* to represent an organizational function as a System — the list above demonstrates that capacity across the breadth of what a real enterprise contains, from Chapter 9's own Manufacturing example through Legal, Security, and Custom Systems built for a need no prior enterprise has had.

**New Systems must not require changes to OSA Core.** This is an architecture rule, not an aspiration (see Chapter 10). A System is built *on* OSA Core — consuming the Enterprise Object model, publishing to the Capability Registry, operating within the orchestration mechanism — never *modifying* Core to accommodate itself. This is what makes `OSA Custom Systems` architecturally possible at all: an enterprise-specific function can be composed as a System using exactly the same foundation every catalogued System above uses, without AI5R re-engineering OSA Core for every customer's particular need.

---

## Chapter 5 — Enterprise Objects

An **Enterprise Object** is a defined unit of business meaning that OSA Systems and AI Workforce reason about consistently, regardless of which System is doing the reasoning. It is the answer to a structural question every fragmented enterprise software stack fails to answer: when Finance, Maintenance, and Procurement each refer to "this pump," are they referring to the same thing, understood the same way? In OSA, the answer is architected to always be yes.

Representative Enterprise Objects span the full breadth of what an enterprise tracks:

*Organizational:* Customer, Employee, Organization, Department, Supplier.
*Commercial and Financial:* Invoice, Purchase Order, Sales Order, Product.
*Operational:* Project, Equipment, Pump, Mechanical Seal, Work Order, Asset, Task.
*Contractual:* LTSA Contract — a Long Term Service Agreement, one example among many possible contract types an enterprise may hold with a customer or supplier.
*Cognitive and Governance:* Knowledge, Document, Capability, Mission, Goal, Decision, Risk, Audit Finding, Compliance Record.

**Why Enterprise Objects are OSA's foundation.** Consider a single Pump, as an Enterprise Object. OSA Maintenance reasons about it as an asset requiring inspection and service. OSA Procurement reasons about it as a source of demand for spare parts. OSA Finance reasons about it as a depreciating asset with a book value. In a fragmented stack, these are three separate records in three separate systems, reconciled — if at all — by a person or an integration project. In OSA, they are three Systems reasoning about one Enterprise Object, each contributing its own perspective to the same underlying entity, with no reconciliation required because there was never a division to reconcile.

This is the architectural mechanism, not merely the philosophical claim, behind Volume I's assertion that OSA Systems share "one data model an enterprise can reason about as a whole." The Enterprise Object is that data model's fundamental unit. Every System is composable with every other System specifically because they are built to operate on the same Enterprise Objects rather than maintaining private, System-specific copies of the same underlying business reality.

---

## Chapter 6 — Capability Architecture

**Capability** is a defined, reusable unit of business function that an OSA System exposes — "Approve Invoice," "Schedule Inspection," "Qualify Lead," "Escalate Risk." A Capability is deliberately smaller than a System and larger than a single action: it is the unit at which business function becomes something AI Workforce can find, invoke, and combine.

**Capability Composition** is the process by which larger business outcomes are assembled from individual Capabilities, often spanning multiple Systems. Resolving a maintenance finding into a completed repair may compose "Schedule Inspection" (OSA Maintenance), "Raise Purchase Order" (OSA Procurement), and "Record Asset Event" (against the relevant Enterprise Object) into one coherent outcome, without any of the three Capabilities needing to know about the other two in advance.

**Capability Discovery** is how AI Workforce, or an OSA System acting on behalf of a goal, locates the Capability appropriate to a given need — not by hardcoded reference, but by matching a need to what is published and available.

**Capability Registry** is where Capabilities are published, catalogued, and versioned — the mechanism that makes Capability Discovery possible. A Capability exists, architecturally, once it is registered; a System that has not published a Capability to the Registry has not made it available to the rest of OSA, regardless of what that System does internally.

**Capability Reuse** follows directly from the Registry's existence. A Capability built to serve one OSA System, or one OSA Instance, is available to every other System and Instance without being rebuilt. This is the architectural mechanism behind Continuous Evolution (Volume I, Chapter 5): a Capability improved once is improved everywhere it is reused, and a Capability built once is not paid for again by the next System or Instance that needs it.

**The System–Workforce boundary.** OSA Systems *expose* Capabilities. AI Workforce *consumes* them. This is a clean, deliberate architectural boundary: a System's responsibility ends at publishing what it can do to the Registry; AI Workforce's responsibility is deciding, in service of a goal, which published Capabilities to invoke and in what sequence. Neither side needs to understand the other's internal design — only the Capability contract between them.

---

## Chapter 7 — AI Workforce Architecture

AI Workforce is structured as a hierarchy of six roles, each operating at a distinct organizational altitude. This is the complete, canonical hierarchy — the same one Volume I introduces at the resolution appropriate to an executive audience. Volume I presents four of these six levels (CEO, Director, Manager, and Employee AI) because those are the levels an executive needs to reason about the workforce as a whole; Volume II adds the two intermediate levels — Executive AI and Specialist AI — that an architect needs to design against. There is one hierarchy, described at two resolutions, not two different hierarchies.

```
                    CEO AI
                       │
                Executive AI
                       │
                 Director AI
                       │
                 Manager AI
                       │
                Specialist AI
                       │
                 Employee AI
```

**CEO AI** operates at the level of the enterprise as a whole — synthesizing outcomes across every OSA System in operation, maintaining a continuously current picture of enterprise performance against its goals.

**Executive AI** operates at the level of a major functional area spanning multiple related Systems — Finance and Treasury together, or Supply Chain across Procurement, Inventory, Warehouse, and Logistics together — providing leadership at a scope broader than any single System but narrower than the whole enterprise.

**Director AI** operates at the level of a single OSA System — setting direction and priority within that System's function, as established in Volume I.

**Manager AI** coordinates a specific workflow or team within a System, assigning work and resolving exceptions within its authority, as established in Volume I.

**Specialist AI** applies deep expertise to a specific class of problem within a workflow — a role distinct from Manager AI's coordination and Employee AI's execution, comparable to a subject-matter expert a human organization would call in for judgment a generalist role cannot provide.

**Employee AI** performs individual units of work to completion, as established in Volume I.

**Delegation** flows downward through this hierarchy: a goal set at the CEO AI level is delegated to the Executive AI level appropriate to it, delegated again to the relevant Director AI, and so on, each level narrowing scope until the goal reaches a role capable of executing it directly.

**Collaboration** operates both within a level (multiple Manager AI roles coordinating a cross-System outcome, as in Chapter 6's Capability Composition example) and across levels (a Specialist AI consulted mid-workflow by a Manager AI that has encountered a problem outside its own competence).

**Decision Flow, Mission Flow, and Goal Flow** describe how intent moves through the hierarchy: a **Goal** is the outcome an enterprise wants; a **Mission** is the bounded body of work undertaken to achieve it; a **Decision** is a specific choice made in service of a Mission, made at the lowest level of the hierarchy competent to make it, escalated upward only when it exceeds that level's authority.

**Escalation** is the formal mechanism for that upward movement — a Specialist AI or Employee AI encountering a decision beyond its authority does not stall; it escalates to the Manager AI or Director AI above it, exactly as a human employee would escalate to a human manager.

**Learning and Continuous Improvement** close the loop: outcomes observed at every level feed back into how AI Workforce performs the next Mission — a pattern architected in full as part of the Runtime Lifecycle in Chapter 9.

**AI Workforce orchestrates OSA Systems; it does not sit beside them.** Every role in this hierarchy acts by invoking Capabilities that OSA Systems expose (Chapter 6) and by acting on Enterprise Objects those Systems share (Chapter 5). AI Workforce is part of OSA — built on the same OSA Core every System is built on — not an external intelligence layer consuming OSA as a service. This is a structural fact, not only a stated principle: there is no architectural boundary between "AI Workforce" and "OSA" for a boundary to be crossed.

---

## Chapter 8 — OSA Instance

An **OSA Instance** is a specific, manufactured deployment of OSA: a defined composition of OSA Systems, staffed by a defined composition of AI Workforce roles, operating on a specific enterprise's own Enterprise Objects.

Every instance moves through the same sequence:

```
Business Discovery → Solution Composition → Manufacturing → Deployment
        → Configuration → Operation → Evolution
```

**Business Discovery** establishes what the enterprise actually needs — its industry, its challenge, its goals — before any System is selected, as established in Volume I.

**Solution Composition** translates that understanding into a specific selection: which OSA Systems this instance requires, and which AI Workforce roles must be staffed to operate them.

**Manufacturing** produces the instance according to the Digital Factory's manufacturing lifecycle (Chapter 2), from that composed specification.

**Deployment** places the manufactured instance into operation for the enterprise.

**Configuration** adapts the deployed instance's operating parameters to the enterprise's specific way of working, distinct from Solution Composition — configuration adjusts how a chosen System behaves; it does not change which Systems were chosen.

**Operation** is the instance functioning as the enterprise's actual operating environment, governed by the Runtime Architecture detailed in Chapter 9.

**Evolution** re-enters the manufacturing lifecycle as the enterprise's needs change, exactly as Chapter 2 describes for OSA generally, now applied to this one instance specifically.

**Example instance compositions**, illustrating how the same architecture produces structurally different instances:

- **Engineering Company:** OSA Engineering, OSA Project, OSA Procurement, OSA Finance.
- **Manufacturing Company:** OSA Manufacturing, OSA Inventory, OSA Maintenance, OSA Procurement, OSA Finance.
- **Retail:** OSA CRM, OSA Inventory, OSA Marketing, OSA Sales, OSA Finance.
- **Hospital:** OSA HR, OSA Procurement, OSA Compliance, OSA Finance, OSA Customer Service.
- **University:** OSA HR, OSA Learning, OSA Finance, OSA CRM, OSA Administration.
- **SME:** OSA Finance, OSA CRM, and one function-specific System matched to the SME's core business.
- **Law Firm:** OSA Legal, OSA Project, OSA CRM, OSA Finance, OSA Document.
- **Consulting Firm:** OSA Project, OSA CRM, OSA Finance, OSA Knowledge, OSA Analytics.

No two instances above share an identical composition, and none required a System to be invented that was not already part of the catalogue in Chapter 4 — the composability this chapter demonstrates is a direct consequence of the architecture established in Chapters 4 through 6, not a separate capability layered on top of it.

**Business View and Engineering View of one lifecycle.** Volume I, Chapter 8 describes this same journey from the business side, as the Customer Journey: Business Challenge → Business Discovery → OSA Manufacturing → OSA Deployment → OSA Instance → AI Workforce → Continuous Evolution. That diagram and this chapter's engineering-level sequence are not two different journeys — they are the same lifecycle, described at the resolution each audience needs, exactly as Chapter 3 establishes for OSA generally:

```
Business View (Volume I, Ch.8)          Engineering View (this chapter)

Business Challenge          ──────►     (precedes Specification; the
                                          unmanufactured trigger for
                                          Business Discovery, not itself
                                          a stage of the instance lifecycle)
Business Discovery          ──────►     Business Discovery
                                         Solution Composition
                                         (the engineering-level translation
                                          of what Business Discovery found
                                          into a specific System selection)
OSA Manufacturing            ──────►     Manufacturing
OSA Deployment                ──────►     Deployment
OSA Instance                  ──────►     Configuration
                                          (the engineering activity of
                                           readying the named, delivered
                                           instance Volume I describes)
AI Workforce                   ──────►     Operation
                                          (the engineering term for the
                                           instance actively running,
                                           workforce included)
Continuous Evolution            ──────►     Evolution
```

Two points follow from this mapping, and both are load-bearing for reading Volume I and Volume II together. First, **Solution Composition has no separate business-side name** because, from the business view, it is part of what Business Discovery accomplishes — the enterprise experiences one discovery conversation, not two. Second, **OSA Instance and AI Workforce (Volume I) map to Configuration and Operation (Volume II)** because Volume I names the *deliverable* at each point (the instance itself, then the workforce operating within it) while Volume II names the *engineering activity* underway at that same point (configuring it, then operating it) — the same moments in the lifecycle, named for what each audience needs to know about them.

---

## Chapter 9 — Runtime Architecture

The Runtime Lifecycle is the path a business goal follows, in an operating OSA Instance, from statement to learned outcome:

```
Business Goal
     │
     ▼
AI Workforce
     │
     ▼
Capability
     │
     ▼
OSA Systems
     │
     ▼
Enterprise Objects
     │
     ▼
Execution
     │
     ▼
Observation
     │
     ▼
Learning
     │
     ▼
Continuous Evolution
```

**Business Goal** is the starting point — an outcome the enterprise wants, stated at whatever level of the AI Workforce hierarchy is appropriate to its scope (Chapter 7).

**AI Workforce** receives the goal and, through Delegation, resolves it to the role and Mission appropriate to carry it out.

**Capability** is what that role invokes — discovered through the Capability Registry (Chapter 6) as the specific, reusable unit of function the Mission requires.

**OSA Systems** are where the invoked Capability actually lives — the System that published it carries out its part of the work.

**Enterprise Objects** are what the Capability acts upon — the shared entities (Chapter 5) the System reads, updates, or creates in the course of carrying out the Capability.

**Execution** is the Capability's work actually being carried out against those Enterprise Objects, within the System that owns it.

**Observation** captures what happened — the outcome of Execution, made visible to the AI Workforce role that initiated it and to any other role with a legitimate interest in the outcome.

**Learning** turns Observation into improved future behavior — not confined to the individual role that acted, but available to the AI Workforce hierarchy broadly, per the Learning principle established in Chapter 7.

**Continuous Evolution** is where Learning closes the loop into the Digital Factory's own manufacturing lifecycle (Chapter 2) — what is learned at runtime can inform how the instance, or OSA itself, is specified and manufactured going forward, completing the connection between how OSA is built and how OSA is run.

This lifecycle is the same for every Business Goal, regardless of which OSA System, which Enterprise Object, or which level of AI Workforce is involved — a single, consistent runtime architecture underlying every OSA Instance's daily operation.

---

## Chapter 10 — Architecture Rules

The layered structure established in Chapter 1 carries specific rules about what belongs where. These rules are what keep OSA composable rather than fragmenting into instance-specific variants over time.

**What belongs to OSA Core.** The Enterprise Object model (Chapter 5), the Capability Registry (Chapter 6), and the orchestration mechanism through which AI Workforce acts on OSA Systems. Nothing System-specific and nothing instance-specific belongs in Core.

**What belongs to OSA Systems.** System-specific Capabilities, published to the Registry; System-specific specializations of Enterprise Objects (a Pump as understood specifically by OSA Maintenance, for instance, while remaining the same underlying Enterprise Object every other System shares); and System-specific workflows composed from those Capabilities.

**What belongs to OSA Instances.** The specific composition of Systems selected for one enterprise, the Configuration applied to that composition, and the specific Enterprise Object data that enterprise's operation produces. Nothing architectural belongs at the instance level — only selection, configuration, and data.

**What belongs to AI Workforce.** The six-level role hierarchy (Chapter 7), the Delegation and Escalation logic that governs how goals and decisions move through it, and the Learning mechanism that improves it over time.

**What belongs to Enterprise Objects.** The canonical definition of each object type and the lifecycle states it can hold — owned centrally, so that every System's understanding of a given Enterprise Object remains the same understanding.

**What may evolve.** New OSA Systems may be introduced. New Enterprise Object types may be defined. New Capabilities may be published and existing ones versioned. New AI Workforce staffing may be composed within an instance — any number of instances of each of the six AI Workforce roles, across any number of Systems. New OSA Instances may be composed at any time. None of this requires a change to OSA Core.

**AI Workforce hierarchy levels, specifically: frozen.** The six-level structure itself (Chapter 7) — CEO AI, Executive AI, Director AI, Manager AI, Specialist AI, Employee AI — is part of the layered architecture, not part of what evolves per instance. What is unlimited is staffing *within* those six levels (stated above); the count and ordering of the levels themselves is fixed, on the same basis as OSA Core's layered structure below.

**What is frozen.** The layered structure itself — Core beneath Systems beneath Instances, with AI Workforce and Enterprise Objects as the shared substrate connecting them — is not subject to redesign by the introduction of a new System, Object, or Instance. The OSA Philosophy established in Volume I (One Company, One Product, Many Systems, One AI Workforce, Business First, Composable Enterprise, Continuous Evolution) governs every evolution described above and is not superseded by any of it. The definition of OSA itself — an Enterprise Operating System, not ERP, not CRM, not Accounting Software — is likewise frozen; extending what OSA Systems exist does not change what category of product OSA is.

---

## Final Summary

Volume II has established how OSA is architected: a layered structure running from AI5R's Digital Factory discipline down through OSA itself, its composable Systems, its shared Enterprise Objects, its AI Workforce, and the specific Instances an enterprise actually runs. Every layer exists because the layer beneath it, alone, could not serve an enterprise completely — and every layer remains stable while the layers above it change, which is what allows OSA to grow without fragmenting.

This structure is not a departure from the vision Volume I set out — it is that vision made architecturally precise. OSA Systems give "Many Systems" a concrete shape. Enterprise Objects give "Composable Enterprise" a shared foundation to compose from. AI Workforce's hierarchy gives "One AI Workforce" an organizational form. The Runtime Lifecycle gives "Continuous Evolution" a mechanism, not only an intention.

Volume II stands, alongside Volume I, as a frozen architectural reference. Future volumes — on individual OSA Systems, on AI Workforce in greater depth, on engineering standards, and on the long-range future of OSA — build on the structure this volume establishes without altering it.
