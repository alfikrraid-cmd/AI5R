**Knowledge ID:** MR-KQ-002
**Title:** Every module must be classified by verifiability at Specification time
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001's modules fell into three distinct classes discovered only during Verification: DB-dependent (Asset, Soot Blower, Work Order, Maintenance History), external-service-dependent in the same way (Dashboard, since it aggregates DB-backed registries), and self-contained (Basic AI Assistant, pure Python, no external dependency). This classification was not stated up front and was only reconstructed afterward for the Manufacturing Report.
**Recommendation:** State each module's verifiability class (DB-dependent / external-service-dependent / self-contained) explicitly at Specification time, so the Verification phase's expectations are known before Assembly begins.
**Reuse Scope:** All future Manufacturing Orders. Reflected in `MANUFACTURING/TEMPLATES/MANUFACTURING-ORDER-TEMPLATE.md`.
