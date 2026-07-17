# Build Pack

Product: LTSA-BRAIN
Module: COLUMN-MAPPING
Table: column_mapping
Primary Key: column_mapping_id
Manufactured under: MWO-LTSA-040C (Universal Tabular Data Acquisition)

Part of the Universal Acquisition Infrastructure — a single Source Column
→ Canonical Attribute pair (examples: "TAG NO" → "Pump Tag", "Equipment" →
"Pump Tag", "Pump Number" → "Pump Tag"), always belonging to exactly one
Mapping Profile (`mapping_profile_id`, FK to
`BUILD-PACKS/BP-MAPPING-PROFILE`'s `mapping_profile`). `is_mandatory`
records whether `canonical_attribute` is a required field, serving the
original work order's "Validate ... Missing Mandatory Values" requirement
generically — there is no per-workbook-type parser anywhere in this
product that could otherwise know this (Architecture Decision item 7).

Full CRUD (Create/List/Detail/Update/Delete), matching Mapping Profile's
own reusable, managed-resource status.
