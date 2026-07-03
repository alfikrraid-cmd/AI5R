# AX-007 Universal Serialization Contract

Status: APPROVED DRAFT  
Layer: Architecture Foundation  
Purpose: Define universal serialization and deserialization rules for AI5R.

## 1. Definition

Serialization is the process of converting AI5R objects, relationships, lifecycle records, events, missions, knowledge, and runtime records into portable data formats.

Deserialization is the process of reconstructing valid AI5R records from serialized data.

## 2. Canonical Format

The canonical serialization format for AI5R is JSON.

All AI5R core records must support:

```text
to_dict()
from_dict()
to_json()
from_json()
