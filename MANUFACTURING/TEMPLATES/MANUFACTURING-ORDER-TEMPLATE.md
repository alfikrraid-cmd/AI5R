# MO-00X — <Product/Module Name>

Manufacturing Order: MO-00X
Product: <name>
Customer: <name, if applicable>
Version: <x.y>
Status: <DRAFT | SPECIFICATION | ASSEMBLY | RELEASE CANDIDATE | RELEASED>

Updated per MR-001 (Manufacturing Review of MO-001) — see `MANUFACTURING/MR-001/MR-001-MANUFACTURING-REVIEW.md` for the evidence this template is based on.

## 1. Manufacturing Vehicle

Which existing product/repository location this order manufactures into, and why (evidence that this is reuse, not a new product).

## 2. Module-by-Module Plan

| # | Module | Manufacturing Decision | Verifiability Class |
|---|---|---|---|
| | | (reuse existing / new, following \<template\>) | DB-dependent / external-service-dependent / self-contained |

**New-module cap:** state explicitly how many net-new modules this order manufactures, and confirm it does not exceed the standing per-order cap (MR-001 Recommendation 2). If it would, split into `MO-00X` and `MO-00X.Y`.

## 3. Schema / Contract Design (if applicable)

Additive only — new tables/fields, nothing existing altered. Document any intentional constraint (e.g., no cross-table foreign key) explicitly, with reasoning — do not silently work around a real design tension or introduce new architecture to resolve it.

## 4. Reused Conventions

Name the exact existing artifact each new module is patterned after (e.g. "follows `BUILD-PACKS/BP-SEAL` exactly"). A Manufacturing Order introducing a genuinely new convention must say so explicitly and justify why no existing one fits.

## 5. Manufacturing Process

```
Specification → Assembly → Verification → Testing → Release Candidate → Release
```
Each phase produces a real artifact.

## 6. Pre-Flight Environment Check (MR-001)

Before attempting Runtime Verification of any module: confirm required services are reachable and required credentials are present. Record the result (present/absent) explicitly, before Assembly begins — not discovered reactively mid-order.

## 7. Out of Scope (MMP boundary)

Stated explicitly, per module or per order.
