# ARCH-012 — Package Dependency Rules

Status: Active

Version: 1.0.0

Owner: AI5R Architecture Board

---

# Purpose

Define package dependency direction for AI5R-SDK to prevent circular dependencies, duplicate engines, and unclear ownership.

---

# Core Rule

Dependencies must flow downward.

Higher-level packages may import lower-level packages.

Lower-level packages must not import higher-level packages.

---

# Canonical Dependency Layers

Layer 0: BASE

Layer 1: GOV

Layer 2: ARCHITECTURE

Layer 3: ENTERPRISE

Layer 4: MANUFACTURING

Layer 5: INTELLIGENCE

Layer 6: RUNTIME

Layer 7: FINANCE

Layer 8: OSA

Layer 9: PRODUCTS

---

# Dependency Direction

Allowed direction:

PRODUCTS
↓
OSA
↓
FINANCE
↓
RUNTIME
↓
INTELLIGENCE
↓
MANUFACTURING
↓
ENTERPRISE
↓
ARCHITECTURE
↓
GOV
↓
BASE

---

# Locked Rules

## BASE

BASE must not import any AI5R package.

BASE is the root package.

## GOV

GOV may reference BASE concepts but should remain mostly documents and policies.

GOV must not import runtime, product, finance, OSA, or manufacturing code.

## ARCHITECTURE

ARCHITECTURE may reference GOV and BASE.

ARCHITECTURE must not depend on product implementation.

## ENTERPRISE

ENTERPRISE may import BASE, GOV, and ARCHITECTURE.

ENTERPRISE must not import MANUFACTURING, FINANCE, OSA, or PRODUCTS.

## MANUFACTURING

MANUFACTURING may import BASE and ENTERPRISE.

MANUFACTURING must not import FINANCE, OSA, or PRODUCTS.

## INTELLIGENCE

INTELLIGENCE may import BASE, ENTERPRISE, and MANUFACTURING only when needed.

INTELLIGENCE must not import PRODUCTS.

## RUNTIME

RUNTIME may import BASE, ENTERPRISE, MANUFACTURING, and INTELLIGENCE.

RUNTIME must not import PRODUCTS.

## FINANCE

FINANCE may import BASE, ENTERPRISE, MANUFACTURING, INTELLIGENCE, and RUNTIME when needed.

FINANCE must not import PRODUCTS.

## OSA

OSA may import shared lower-level packages.

OSA must not be imported by BASE, ENTERPRISE, MANUFACTURING, FINANCE, or RUNTIME.

## PRODUCTS

PRODUCTS may import shared packages.

PRODUCTS is the highest layer.

No shared package may import PRODUCTS.

---

# Forbidden

- Circular dependency
- Lower-level importing higher-level package
- Product logic inside shared package
- Finance importing Products
- Manufacturing importing Products
- Enterprise importing Manufacturing
- BASE importing anything from AI5R-SDK

---

# Architecture Gate

Before adding an import, answer:

1. Is the imported package lower-level?
2. Does this create circular dependency?
3. Does this violate package ownership?
4. Does this create product logic inside shared packages?
5. Can this be solved through a definition instead?

---

# Canonical Principle

AI5R must remain dependency-directed.

Dependencies must never become a spider web.
