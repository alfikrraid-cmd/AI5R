# ARCH-011 — AI5R SDK Structure

Status: Active

Version: 1.0.0

Owner: AI5R Architecture Board

---

# Purpose

Define the canonical structure of AI5R-SDK to prevent folder sprawl, duplicate engines, and unclear package ownership.

---

# Core Rule

A concept does not automatically become a folder.

Folders exist only when there is a real implementation responsibility.

---

# Canonical SDK Structure

AI5R-SDK may contain these top-level package families:

- BASE
- GOV
- ARCHITECTURE
- ENTERPRISE
- MANUFACTURING
- INTELLIGENCE
- RUNTIME
- OSA
- FINANCE
- PRODUCTS

---

# Folder Responsibilities

## BASE

Contains shared base contracts only.

Allowed:

- BaseDefinition
- BaseObject
- BaseEvent
- BaseRuntime

Not allowed:

- Business logic
- Product logic
- Vertical logic
- Factory-specific logic

## GOV

Contains governance documents and policies.

Allowed:

- Vision
- Principles
- Reuse First
- Cost First AI
- Architecture Board
- Governance rules

Not allowed:

- Runtime code
- Business logic

## ARCHITECTURE

Contains architecture decisions, architecture indexes, and structure rules.

Allowed:

- Architecture documents
- Architecture tests
- Architecture indexes
- Dependency rules

Not allowed:

- Runtime business implementation

## ENTERPRISE

Contains Enterprise Core implementation.

Allowed:

- EnterpriseObject
- EnterpriseEvent
- EnterpriseKernel
- EnterpriseKnowledgeGraph
- Enterprise Operating Stack

Not allowed:

- Product-specific logic
- Duplicate object engines

## MANUFACTURING

Contains Digital Factory manufacturing contracts and orchestration.

Allowed:

- Manufacturing Order
- DBOM
- Recipe
- Production Line
- Station
- Scheduler
- QA
- Packaging
- Deployment

Not allowed:

- Product-specific engines
- Duplicate workflow engines
- Duplicate object engines

## INTELLIGENCE

Contains cognitive and intelligence capabilities.

Allowed:

- Knowledge
- Memory
- Reasoning
- Decision
- Recommendation
- Learning

Not allowed:

- Product-specific shortcuts

## RUNTIME

Contains runtime execution infrastructure.

Allowed:

- Runtime core
- Runtime registry
- Runtime adapters
- Execution state

Not allowed:

- Product-specific runtime duplication

## OSA

Contains Organization System Architecture implementation.

Allowed:

- Organization runtime
- Organization agents
- Organization services

Not allowed:

- Canonical engine duplication

## FINANCE

Contains finance and accounting implementation.

Allowed:

- Chart of Accounts
- Journal Entry
- Ledger
- Accounting rules

Not allowed:

- Direct vertical journal engines
- Duplicate accounting engines

## PRODUCTS

Contains shipped or productized outputs.

Allowed:

- LTSA Brain
- AI5R Studio
- Customer-specific products

Not allowed:

- Canonical engines that belong in shared packages

---

# Package Creation Rule

Before creating a new top-level folder, answer:

1. Is this a real implementation responsibility?
2. Can it fit an existing package?
3. Is it only a concept, not a package?
4. Will it create duplicate engines?
5. Has ARCH-000 been checked?

If an existing package can own it, do not create a new folder.

---

# Anti-Sprawl Principle

AI5R must prefer fewer stronger packages over many weak packages.

---

# Locked Principle

Concepts become documents first.

Only implementation responsibilities become packages.
