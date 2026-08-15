"""MWO-LTSA-074 -- Validation stage.

Reuses FACTORY.CORE.exceptions.ManufacturingValidationError unmodified
(a one-line ValueError subclass, the same exception every existing Factory
Pack station already raises via BaseManufacturingStation.validate()) rather
than inventing a parallel exception type.

Each required-field list below is not invented -- it mirrors the real
NOT NULL / PRIMARY KEY constraints already enforced by
PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql for the corresponding
table, so a package that passes validation here would also pass a real
INSERT against that table (modulo FK/CHECK constraints, which are the
Relationship Resolution stage's job, not Validation's).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.CORE.exceptions import ManufacturingValidationError  # noqa: E402

# entity_name -> required field names, matching each table's real NOT NULL
# columns (CANONICAL_SCHEMA.sql).
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "pump": ("tag_number",),
    "installation": ("installation_code", "report_no"),
    "seal": ("seal_code",),
    "drawing": ("document_code", "seal_code", "title", "document_type"),
    "pm": ("pm_occurrence_code", "pm_schedule_code"),
    "cm": ("condition_monitoring_reading_code", "condition_monitoring_schedule_code"),
    "failure": ("cm_report_code", "failure_category", "severity", "failure_description"),
    "workorder": ("work_order_code",),
    "document": ("document_code", "seal_code", "title", "document_type"),
}


def _has_value(value: Any) -> bool:
    """Treats a whitespace-only string as absent -- this validator is a
    standalone, reusable component (not only ever called after
    knowledge_normalizers.normalize_dict), so it must not assume its input
    was already normalized."""
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def validate_entity(entity_name: str, data: dict[str, Any] | None) -> None:
    """Raises ManufacturingValidationError naming every missing required
    field at once (not just the first) -- one clear report, not a slow
    field-by-field discovery loop."""
    required = REQUIRED_FIELDS.get(entity_name)
    if required is None:
        raise ManufacturingValidationError(f"Unknown entity_name {entity_name!r} -- no validation rule exists for it")

    data = data or {}
    missing = [field_name for field_name in required if not _has_value(data.get(field_name))]
    if missing:
        raise ManufacturingValidationError(
            f"{entity_name}: missing required field(s): {', '.join(missing)}"
        )


def validate_package(normalized: dict[str, Any]) -> None:
    """Validates every entity present in a normalized extraction. Absent
    entities (None, or an empty list) are skipped -- not every source
    document carries every one of the 9 entity types, and that is a real,
    honest fact about the source, never an error."""
    if normalized.get("pump"):
        validate_entity("pump", normalized["pump"])
    if normalized.get("installation"):
        validate_entity("installation", normalized["installation"])
    if normalized.get("seal"):
        validate_entity("seal", normalized["seal"])
    if normalized.get("drawing"):
        validate_entity("drawing", normalized["drawing"])
    for pm in normalized.get("pm") or []:
        validate_entity("pm", pm)
    for cm in normalized.get("cm") or []:
        validate_entity("cm", cm)
    for failure in normalized.get("failure") or []:
        validate_entity("failure", failure)
    for workorder in normalized.get("workorder") or []:
        validate_entity("workorder", workorder)
    for document in normalized.get("documents") or []:
        validate_entity("document", document)
