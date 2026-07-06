# AI5R Knowledge Lifecycle Specification

Status:
Draft

Version:
1.0

---

## Purpose

This specification defines how knowledge is created, evaluated, validated, promoted, revised, deprecated, and archived inside AI5R.

AI5R treats knowledge as an evolving first-class asset.

Knowledge is not assumed to be final.

---

## Core Principle

Code follows Architecture.

Architecture follows Theory.

Theory follows Research.

Research follows Reality.

---

## Knowledge Lifecycle

Reality
↓
Observation
↓
Evidence
↓
Question
↓
Hypothesis
↓
Research
↓
Theory
↓
Validation
↓
Validated Knowledge
↓
Standard
↓
Implementation
↓
Operational Experience
↓
Revision

---

## Knowledge Status

Knowledge may have one of the following statuses:

- DRAFT
- OBSERVED
- RESEARCHING
- HYPOTHESIS
- THEORY
- EXPERIMENTAL
- VALIDATED
- STANDARD
- LEGACY
- DEPRECATED
- ARCHIVED

---

## Promotion Rules

A knowledge item may be promoted only when it has sufficient supporting evidence.

Promotion path:

DRAFT
↓
OBSERVED
↓
RESEARCHING
↓
HYPOTHESIS
↓
THEORY
↓
EXPERIMENTAL
↓
VALIDATED
↓
STANDARD

---

## Deprecation Rules

Knowledge may be deprecated when:

- stronger evidence contradicts it
- it is replaced by a newer validated version
- it no longer applies to current architecture
- it creates unacceptable operational risk

Deprecated knowledge SHALL NOT be deleted.

It SHALL remain traceable.

---

## Versioning

Knowledge SHOULD follow semantic versioning:

MAJOR.MINOR.PATCH

Examples:

1.0.0

1.1.0

2.0.0

MAJOR changes alter meaning.

MINOR changes add clarification or scope.

PATCH changes fix wording or minor errors.

---

## Lineage

Every important knowledge item SHOULD define:

- origin observation
- related research question
- hypothesis
- supporting evidence
- validation method
- related theory
- related architecture
- related SDK modules
- related products

---

## Audit Principle

Every decision made by AI5R SHOULD be traceable to the knowledge, evidence, and observations from which it originated.

---

## Knowledge Review

Knowledge review SHOULD include:

- evidence review
- source review
- risk review
- architecture impact review
- product impact review
- backward compatibility review

---

## Final Rule

Knowledge is never final.

Knowledge is continuously evaluated, challenged, and improved through evidence, validation, and operational experience.
