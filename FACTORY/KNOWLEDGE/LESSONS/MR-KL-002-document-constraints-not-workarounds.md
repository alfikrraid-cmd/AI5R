**Knowledge ID:** MR-KL-002
**Title:** Document a real design constraint explicitly rather than silently working around it or inventing new architecture
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001's Work Order and Maintenance History modules needed to reference an asset that could live in any of four separate registries (pump, seal, asset, soot blower) with no common supertype table. Rather than inventing a new supertype table (new architecture, out of scope) or silently adding an unenforced-but-undocumented reference, the polymorphic `(asset_code, asset_type)` pair was used and the constraint was written down explicitly in the Specification and in DDL comments.
**Recommendation:** When a genuine design tension is found during manufacturing that has no clean resolution within existing architecture, document the constraint and the reasoning explicitly rather than silently working around it or unilaterally introducing new architecture to resolve it.
**Reuse Scope:** All future Manufacturing Orders encountering a cross-entity reference with no existing supertype or shared contract.
