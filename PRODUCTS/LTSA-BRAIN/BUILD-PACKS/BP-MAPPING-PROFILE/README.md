# Build Pack

Product: LTSA-BRAIN
Module: MAPPING-PROFILE
Table: mapping_profile
Primary Key: mapping_profile_id
Manufactured under: MWO-LTSA-040C (Universal Tabular Data Acquisition)

Part of the Universal Acquisition Infrastructure — the extension point for
customer-specific column names (Architecture Decision item 8): "Mapping
Profile defines how customer-specific column names map to canonical LTSA
attributes" (Business Purpose), and "Mapping Profiles must be reusable"
(Business Rule). `workbook_type` scopes which of the 11 Supported Workbook
Types a profile's `column_mapping` rows target — a Pump Master profile and
a Seal Stock profile cannot share source-column vocabulary. `customer` is
free text (examples given include "Internal LTSA," which is not a
`customer_registry` entry, so a foreign key would not fit).

Full CRUD (Create/List/Detail/Update/Delete) — a managed, editable
resource, not an immutable structural fact. Customer-specific column
handling always goes through profile data, never code (Architecture
Decision item 7).
