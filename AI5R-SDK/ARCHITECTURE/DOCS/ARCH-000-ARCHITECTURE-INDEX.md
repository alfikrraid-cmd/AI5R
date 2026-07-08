# ARCH-000 — AI5R Architecture Index

## Purpose

This document is the master index of AI5R architecture decisions.

Every new architecture document must be registered here to prevent duplicate architecture, duplicate engines, and conflicting design decisions.

## Core Rule

Do not create a new architecture, engine, runtime, module, or domain model before checking this index.

## Architecture Families

### Canonical Architecture

- AX — Canonical Cognitive Architecture
- ARCH — Enterprise OS Architecture
- ENT — Enterprise Core Architecture
- FIN — Enterprise Finance Architecture

## Current Architecture Registry

| Code | Title | Status | Source of Truth |
|---|---|---|---|
| ARCH-000 | Architecture Index | Active | Yes |
| ARCH-009 | Business Capability Architecture | Active | Yes |
| ENT-003 | Enterprise Operating Stack | Active | Yes |
| EAA-001A | Standard Enterprise Accounting Architecture | Active | Yes |
| FIN-002 | Chart of Accounts | Active | Yes |

## Locked Principles

1. AI5R is an Enterprise Operating System.
2. Every Business OS must reuse the Enterprise Kernel.
3. Every business object must use EnterpriseObject.
4. Every relationship must use Enterprise Knowledge Graph.
5. Every vertical must pass through Business Capability.
6. Every business process starts from EnterpriseDocument.
7. Every EnterpriseDocument must pass through EnterpriseWorkflow.
8. Only completed workflows may produce EnterpriseTransaction.
9. No vertical module may create journal entries directly.
10. Only EnterpriseAccounting may translate transactions into Journal Entry and General Ledger.
11. No duplicate engines.
12. Reuse existing modules whenever possible.

## Before Creating New Architecture

Check:

1. Does an existing architecture already define this concept?
2. Is this a new capability or only a variation of an existing capability?
3. Should this belong to Enterprise Core instead of a vertical?
4. Will this create a duplicate engine?
5. Does this reuse EnterpriseObject, EnterpriseEvent, EnterpriseKnowledgeGraph, and EnterpriseKernel?

## Next Planned Architecture Documents

| Code | Title | Purpose |
|---|---|---|
| ARCH-010 | Enterprise Domain Model | Define domains, capabilities, documents, workflows, transactions |
| ARCH-011 | Enterprise Document Lifecycle | Define standard document lifecycle |
| ARCH-012 | Enterprise Workflow Architecture | Define workflow model and approval flow |
| ARCH-013 | Enterprise Transaction Architecture | Define transaction contract and registry |
