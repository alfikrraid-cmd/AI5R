# ADR-006 — Canonical Product Definition

**Date:** 2026-07-12
**Status:** ACCEPTED
**Reviewer:** AI CTO
**Evidence base:** `ENGINEERING/REVIEWS/LTSA-Canonical-Definition-Review.md` (v1)

---

## Context

The LTSA Canonical Definition Review (v1) audited every current candidate surface in the repository for a canonical product/identity definition — `REGISTRY/SYSTEM/system_manifest.json`, the tracked `CONSTITUTION/` tree, the legacy `REGISTRY/CONTITUTION/` tree, the tracked `ADR/` and `ROADMAP/` trees, and the populated content sitting inside `AI5R-Repository-Pack-v1.0.zip` / its untracked extraction.

Findings: multiple surfaces (`system_manifest.json`, `ADR-0001`) already assert that AI5R's canonical identity/memory lives in the repository, not in chat. But no document anywhere in the repository — tracked, legacy, or zip-packaged — is currently populated as a "Product Definition." The tracked, official `CONSTITUTION/` and `ROADMAP/PRODUCT.md` files are empty scaffolding; the only populated Constitution content exists solely inside an untracked zip extraction.

This ADR does not resolve where that definition will physically live or how it will be populated — that is deferred to a follow-up Mission Work Order (MWO) per the standard governance sequence (Evidence → Review → ADR → MWO → Implementation). It records the governing principle only.

---

## Decision

Canonical Product Definition becomes the Single Source of Truth (SSOT) for every AI5R product.

Any product-level fact (identity, scope, roadmap, or specification) that is not recorded in the designated Canonical Product Definition is not authoritative, regardless of where else it may appear (chat, zip packages, legacy trees, or duplicate scaffolding).

No existing document in the repository currently satisfies this role (see `LTSA-Canonical-Definition-Review.md`, Finding 6). Designating, locating, and populating that document is out of scope for this ADR and is deferred to a follow-up MWO.

---

## Consequences

### Easier

- Establishes a single governing principle against which every future product-definition surface (tracked, legacy, or packaged) can be evaluated.
- Gives the follow-up MWO a clear mandate: designate and populate the canonical location, rather than debating whether one should exist.
- Aligns with the existing `ADR-0001` principle ("AI5R's canonical memory and identity will live in the GitHub repository") by extending the same SSOT logic specifically to product definition.

### Harder

- Until the follow-up MWO designates and populates an actual file, this ADR has no enforcement target — any of the empty or duplicate surfaces identified in the Review could still be mistaken for authoritative.
- Existing duplicate/empty surfaces (`CONSTITUTION/` vs `REGISTRY/CONTITUTION/` vs `RepositoryPack/.../CONSTITUTION/`) are not resolved by this decision alone and remain a source of confusion until migration work (tracked separately, see `RC-002`) is complete.

---

## Related

- `ENGINEERING/REVIEWS/LTSA-Canonical-Definition-Review.md` — evidence base for this decision.
- `ENGINEERING/RC/RC-002-Repository-Case-Normalization.md` — related unresolved duplication defect (`REGISTRY/` vs `registry/`).
- `RepositoryPack/AI5R-Repository-Pack-v1.0/ADR/ADR-0001-AI5R-Lives-In-Repository.md` — prior related decision on canonicality of the repository itself.

---

## Next Step

Per governance workflow: this ADR is followed by a Mission Work Order (MWO) to designate and populate the canonical Product Definition location. No MWO has been created as part of this ADR.
