# Factory Knowledge Index

All entries originate from FK-001 (Factory Knowledge Integration), sourced exclusively from MR-001 (Manufacturing Review of MO-001) and the real manufacturing evidence it reviewed. No item here is speculative — each cites its evidence and source.

## MANUFACTURING_RULES/

| ID | Title |
|---|---|
| [MR-KR-001](MANUFACTURING_RULES/MR-KR-001-attempt-real-execution-when-possible.md) | Attempt real execution wherever the environment genuinely allows it |
| [MR-KR-002](MANUFACTURING_RULES/MR-KR-002-separate-structural-from-runtime-verification.md) | State structural validation and runtime verification as two distinct fields |
| [MR-KR-003](MANUFACTURING_RULES/MR-KR-003-cap-new-module-count-per-order.md) | Cap new-module count per Manufacturing Order |
| [MR-KR-004](MANUFACTURING_RULES/MR-KR-004-never-truncate-verification-output.md) | Never truncate verification runner output when completeness matters |
| [MR-KR-005](MANUFACTURING_RULES/MR-KR-005-preflight-environment-check.md) | Perform a pre-flight environment-capability check before Assembly |

## PATTERNS/

| ID | Title |
|---|---|
| [MR-KP-001](PATTERNS/MR-KP-001-bp-seal-registry-shape.md) | BP-SEAL registry shape — proven reusable CRUD template |
| [MR-KP-002](PATTERNS/MR-KP-002-verification-runner-glob-discovery.md) | Glob-based test discovery requires no maintenance as modules grow |
| [MR-KP-003](PATTERNS/MR-KP-003-brain-consumed-unmodified-by-product.md) | AI5R-SDK/BRAIN's pipeline interface is consumable by a product unmodified |

## QUALITY_GATES/

| ID | Title |
|---|---|
| [MR-KQ-001](QUALITY_GATES/MR-KQ-001-structural-vs-runtime-determination.md) | Structural Validation and Runtime Verification as separate mandatory gates |
| [MR-KQ-002](QUALITY_GATES/MR-KQ-002-verifiability-classification.md) | Every module classified by verifiability at Specification time |
| [MR-KQ-003](QUALITY_GATES/MR-KQ-003-verification-completion-marker-check.md) | Confirm a verification runner reached its own completion marker |

## LESSONS/

| ID | Title |
|---|---|
| [MR-KL-001](LESSONS/MR-KL-001-real-execution-finds-real-defects.md) | Real execution finds real defects structural review cannot |
| [MR-KL-002](LESSONS/MR-KL-002-document-constraints-not-workarounds.md) | Document a real design constraint rather than working around it |
| [MR-KL-003](LESSONS/MR-KL-003-bundling-blurs-confidence.md) | Bundling modules of different verifiability blurs confidence levels |

---

Every item's `Reuse Scope` states where it applies going forward. See `MANUFACTURING/TEMPLATES/` for the two templates these rules and gates are already reflected in.
