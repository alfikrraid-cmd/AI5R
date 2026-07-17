# Build Pack

Product: LTSA-BRAIN
Module: SEAL-STOCK
Table: seal_stock
Primary Key: seal_code
Manufactured under: MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing)

Seal Stock belongs to Mechanical Seal, not Pump — one stock record per
`seal_code`, referencing `BUILD-PACKS/BP-SEAL`'s `seal_registry` by foreign
key. Never keyed by pump.
