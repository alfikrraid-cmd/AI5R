# Build Pack

Product: LTSA-BRAIN
Module: SEAL-PUMP-COMPATIBILITY
Table: seal_pump_compatibility
Primary Key: (seal_code, pump_tag_number) — composite
Manufactured under: MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing)

One Mechanical Seal may fit multiple Pumps; one Pump may accept multiple
compatible seals (MWO-LTSA-030 Business Rules) — many-to-many, hence a
composite key rather than a surrogate one. `seal_code` references
`BUILD-PACKS/BP-SEAL`'s `seal_registry`; `pump_tag_number` references the
canonical Pump Registry at `MODULES/PUMP` (`ltsa_pumps.tag_number`) — never
the deprecated `BUILD-PACKS/BP-PUMP` (`pump_registry`), per Architecture
Decision item 3.

Detail/Update/Delete require both `seal_code` and `pump_tag_number` query
parameters, since neither alone identifies a unique row.
