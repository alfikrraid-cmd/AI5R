# AI5R Repository Architecture

Version: 1.0.0
Status: DRAFT

---

# Mission

Define the official repository architecture for AI5R.

This document specifies the purpose, ownership, and lifecycle of every top-level directory.

---

# Repository Structure

```text
AI5R/
├── ADR/
├── ARCHITECTURE/
├── BOOTSTRAP/
├── CONSTITUTION/
├── CORE-SERVICES/
├── DOCS/
├── FACTORIES/
├── REGISTRY/
├── RELEASES/
├── ROADMAP/
├── SYSTEM/
├── TESTS/
```

---

# Directory Responsibilities

## ADR

Architecture Decision Records.

Contains all engineering decisions that have long-term impact.

---

## ARCHITECTURE

System blueprints.

Platform diagrams.

Repository architecture.

Runtime architecture.

Factory architecture.

---

## BOOTSTRAP

Entry point for AI5R.

Contains startup instructions, loading sequence, and current project state.

---

## CONSTITUTION

Defines AI5R principles.

Mission.

Values.

Decision framework.

Prompt rules.

Engineering standards.

---

## CORE-SERVICES

Reusable platform services.

Kernel.

Memory.

Git integration.

Release pipeline.

Reviewer.

DNA.

Deploy.

---

## DOCS

General documentation that is not part of platform governance.

---

## FACTORIES

Production engines.

Book Factory.

Developer Factory.

Website Factory.

OSA Factory.

Education Factory.

Video Factory.

Activity Factory.

---

## REGISTRY

Platform registry.

Official manifests.

Service registrations.

Workflow registrations.

Prompt registry.

Artifacts.

Migration reports.

Cleanup reports.

---

## RELEASES

Versioned releases.

---

## ROADMAP

Future planning.

Product roadmap.

Mission roadmap.

Sprint roadmap.

---

## SYSTEM

Runtime configuration.

System configuration.

Execution schemas.

Global configuration files.

---

## TESTS

Validation.

Integration tests.

Regression tests.

---

# Governance Rules

No feature may create a new top-level directory without architecture approval.

All platform metadata must reside under REGISTRY.

All runtime configuration belongs to SYSTEM.

All business modules belong to FACTORIES.

All governance documents belong to ARCHITECTURE or CONSTITUTION.
