# AX-005 Universal Relationship Contract

Status: APPROVED DRAFT  
Layer: Architecture Foundation  
Purpose: Define the universal relationship contract between AI5R objects.

## 1. Definition

A Universal Relationship defines how one AI5R object is connected to another AI5R object.

Relationships are first-class architecture records.

No AI5R object should hardcode domain-specific foreign keys when the relationship can be represented as a Universal Relationship.

## 2. Relationship Principles

1. Relationships connect Universal Objects.
2. Relationships must be explicit.
3. Relationships must be auditable.
4. Relationships must be typed.
5. Relationships may carry metadata.
6. Relationships may have lifecycle status.
7. Relationships may belong to a Digital Thread.
8. Relationships must be serializable to JSON.

## 3. Canonical Relationship Fields

| Field | Required | Description |
|---|---:|---|
| id | Yes | Globally unique relationship identifier |
| code | Yes | Human-readable relationship code |
| type | Yes | Relationship type |
| source_object_id | Yes | Source object identifier |
| target_object_id | Yes | Target object identifier |
| status | Yes | Relationship lifecycle status |
| version | Yes | Relationship contract version |
| direction | Yes | Directed or bidirectional |
| weight | No | Relationship strength or priority |
| metadata | No | System-level metadata |
| properties | No | Domain-specific relationship properties |
| created_at | Yes | Creation timestamp |
| updated_at | Yes | Last update timestamp |
| thread_id | No | Digital Thread reference |
| policy_ids | No | Policy references |
| checksum | No | Integrity checksum |

## 4. Canonical Relationship Types

Recommended base types:

```text
owns
belongs_to
contains
depends_on
produces
consumes
assigned_to
governed_by
derived_from
references
executes
observes
controls
learns_from
improves
