**Knowledge ID:** MR-KR-003
**Title:** Cap new-module count per Manufacturing Order; split oversized orders into MO-00X.Y follow-ons
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001 bundled six modules of two categorically different verifiability classes (four DB-dependent registries, one dependent Dashboard aggregation, one self-contained AI Assistant) under a single Release Candidate determination. The order's overall status was gated by its weakest-verified pieces even though the Basic AI Assistant carried strictly stronger evidence (real execution). This blurred confidence levels that should have stayed visible and separate.
**Recommendation:** Limit a single Manufacturing Order to modules of comparable verifiability class where practical, or explicitly break out a self-contained/independently-verifiable module into its own order. State a new-module count and verifiability mix explicitly at Specification time so oversized or mixed-confidence orders are visible before Assembly begins, not discovered after the fact.
**Reuse Scope:** All future Manufacturing Orders, at the Specification phase. Already reflected in `MANUFACTURING/TEMPLATES/MANUFACTURING-ORDER-TEMPLATE.md`'s "New-module cap" field.
