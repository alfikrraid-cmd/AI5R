# GOV-005 — Reuse Before Create

Status: Canonical

Version: 1.0.0

Owner: AI5R Architecture Board

---

# Purpose

Prevent duplicate engines and duplicated implementations.

AI5R prefers extending existing canonical engines instead of creating new ones.

---

# Canonical Law

There shall be only one canonical implementation of every concept.

One Concept

↓

One Canonical Engine

↓

Many Definitions

↓

Many Products

---

# Priority

Every implementation must follow this order.

1. Reuse existing Definition.

2. Extend existing Definition.

3. Reuse existing Canonical Engine.

4. Extend existing Canonical Engine.

5. Create a new Canonical Engine only after Architecture Board approval.

---

# Engine vs Definition

Canonical Engine

↓

Definition

↓

Runtime

↓

Product

Definitions may grow.

Canonical Engines should remain stable.

---

# Forbidden

The following are prohibited without Architecture Board approval.

- Duplicate Engine

- Parallel Runtime

- Similar Engine with different names

- Copy-Paste Engine

---

# Architecture Gate

Before creating a new engine answer:

[ ] Does a Canonical Engine already exist?

[ ] Can the existing Definition be extended?

[ ] Can Configuration solve the problem?

[ ] Can Policy solve the problem?

[ ] Can Recipe solve the problem?

Only if every answer is NO may a new Canonical Engine be proposed.

---

# Examples

Correct

Workflow Engine

↓

ERP Workflow

Website Workflow

Marketing Workflow

HR Workflow

Incorrect

ERP Workflow Engine

Website Workflow Engine

HR Workflow Engine

---

Recipe Engine

↓

Website Recipe

ERP Recipe

Presentation Recipe

Chatbot Recipe

Correct

---

# Canonical Principle

AI5R prefers extending Definitions over creating Engines.

