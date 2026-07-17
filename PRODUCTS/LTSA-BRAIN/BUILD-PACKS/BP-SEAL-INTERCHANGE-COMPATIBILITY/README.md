# Build Pack

Product: LTSA-BRAIN
Module: SEAL-INTERCHANGE-COMPATIBILITY
Table: seal_interchange_compatibility
Primary Key: (seal_code, compatible_seal_code) — composite
Manufactured under: MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing)

A Mechanical Seal may be substituted by another manufacturer's seal (e.g.
JC-100, JC-102, Flowserve-210 in MWO-LTSA-030's worked example) —
self-referential many-to-many against `BUILD-PACKS/BP-SEAL`'s
`seal_registry`, both sides FK'd to the same table. `CHECK (seal_code <>
compatible_seal_code)` prevents a seal being recorded as its own
interchange.

Detail/Update/Delete require both `seal_code` and `compatible_seal_code`
query parameters, since neither alone identifies a unique row. The
relationship is directional as stored (row order matters for a single
lookup); callers wanting the reverse direction query with the two
parameters swapped.
