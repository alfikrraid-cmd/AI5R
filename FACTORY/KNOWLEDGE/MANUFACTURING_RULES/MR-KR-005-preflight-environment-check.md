**Knowledge ID:** MR-KR-005
**Title:** Perform a pre-flight environment-capability check before attempting Runtime Verification, not reactively mid-order
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001 discovered its database-credential gap reactively, mid-order, via an ad hoc `pg_isready`/environment-variable check performed only when Runtime Verification was already being attempted. This mirrored the identical, already-known condition from MWO-P-006/RV-004, meaning the gap was rediscovered rather than checked for up front.
**Recommendation:** Every Manufacturing Order should perform and record a pre-flight environment-capability check (required credentials present? required services reachable?) as an explicit first step of the Assembly phase, before any module-specific work begins — not as a discovery made in the middle of Verification.
**Reuse Scope:** All future Manufacturing Orders. Already reflected in `MANUFACTURING/TEMPLATES/MANUFACTURING-ORDER-TEMPLATE.md`'s "Pre-Flight Environment Check" section.
