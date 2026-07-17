**Knowledge ID:** MR-KR-002
**Title:** State "structurally validated" and "actually executed" as two distinct, named fields in every Manufacturing Report
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001's own report distinguished these informally, module by module, but no prior Manufacturing Order document had made this a named, mandatory field. The distinction proved load-bearing: five of six new modules were structurally validated only (blocked on a missing database credential), while the sixth (Basic AI Assistant) was genuinely executed — conflating the two in a single report would have overstated the five and understated the sixth.
**Recommendation:** Every Manufacturing Report and Quality Gate must record Structural Validation and Runtime Verification as separate, independently-stated determinations (PASS/WARNING/BLOCKER each), never one implying the other.
**Reuse Scope:** All future Manufacturing Reports and Quality Gates. Already reflected in `MANUFACTURING/TEMPLATES/QUALITY-GATE-TEMPLATE.md`.
