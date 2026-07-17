**Knowledge ID:** MR-KP-001
**Title:** The BP-SEAL registry shape is a proven, reusable manufacturing template for CRUD registries
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL`'s shape — a TEXT-PK Object, a graceful pre-insert conflict-check Create workflow, Detail/List/Update/Delete workflows with real embedded SQL, and TEST scripts sourcing `VERIFICATION/lib/psql_common.sh` — was reused four times in MO-001 (Asset Registry, Soot Blower Registry, Work Order, Maintenance History) with zero redesign and zero new architectural decisions. Each new module was a substitution of table/field names against this exact template.
**Recommendation:** Any future Manufacturing Order manufacturing a new CRUD-shaped registry should pattern it against `BUILD-PACKS/BP-SEAL` by default, rather than designing a new shape, unless a documented, evidence-based reason exists that this shape does not fit.
**Reuse Scope:** Any future product or module requiring a simple, single-entity CRUD registry with n8n + PostgreSQL.
