# Build Pack

Product: LTSA-BRAIN
Module: KNOWLEDGE-SOURCE
Table: knowledge_source_registry
Primary Key: knowledge_source_id (immutable)
Manufactured under: MWO-LTSA-040A (Knowledge Source Registry)

The canonical registry for engineering knowledge source provenance inside
LTSA (Architecture Decision item 4). Deliberately **not**
`AI5R-SDK/KNOWLEDGE`'s `KnowledgeSource`/`KnowledgeSourceRegistry` — that
package is frozen, AI5R-platform-level, and explicitly not reused,
modified, or integrated with by this MWO (Architecture Decision items
1-2). The identical name is a known, deliberate collision between two
unrelated artifacts, not an oversight.

This module only manages provenance: no OCR, no PDF extraction, no Excel
parsing, no video analysis, no AI reasoning. Every field is caller-supplied
metadata.

**No Delete operation exists** — the original engineering source must
never be removed by Engineering Knowledge Acquisition (Business Rule;
Architecture Decision item 9). Only Create, List, Detail, Update are
built.

The relationship to Engineering Document (`seal_engineering_document`,
`BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT`) is logical only in this MWO —
no foreign key is added in either direction. Physical linkage is deferred
to MWO-LTSA-040B (Architecture Decision item 6). Installation Event,
Inspection Event, Failure Event, and Engineering Media do not exist yet
and are reserved for future MWOs (040B–040F).
