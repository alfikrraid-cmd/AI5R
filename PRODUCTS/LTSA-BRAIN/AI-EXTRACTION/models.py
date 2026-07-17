"""Normalized data model for the AI Extraction Capability.

Any provider (ClaudeExtractionProvider today; future providers later) must
produce this exact shape, so the LTSA workflow that consumes it never
changes when a provider is added or swapped. See ExtractionProvider in
extraction_provider.py for the interface contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

DOCUMENT_TYPES: tuple[str, ...] = (
    "MECHANICAL_SEAL_INSTALLATION_REPORT",
    "PUMP_DATASHEET",
    "MECHANICAL_SEAL_DRAWING",
    "PUMP_DRAWING",
    "NAMEPLATE",
    "UNKNOWN",
)

# Minimum Fields (MVP): General + Pump + Mechanical Seal + Process.
FIELD_NAMES: tuple[str, ...] = (
    "customer",
    "end_user",
    "date",
    "location",
    "pump_manufacturer",
    "pump_model",
    "pump_size",
    "pump_speed",
    "pump_rotation",
    "pump_equipment_number",
    "seal_manufacturer",
    "seal_type",
    "seal_drawing_number",
    "seal_material_code",
    "seal_api_plan",
    "seal_location",
    "process_liquid",
    "process_temperature",
    "process_pressure",
    "process_specific_gravity",
    "process_viscosity",
)


@dataclass(frozen=True)
class FieldValue:
    value: Optional[Union[str, float]]
    confidence: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "confidence": self.confidence}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FieldValue":
        return FieldValue(value=data.get("value"), confidence=data.get("confidence"))


@dataclass(frozen=True)
class ExtractionResult:
    document_type: str
    document_type_confidence: Optional[float]
    fields: dict[str, FieldValue]
    ocr_text: str
    provider: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "document_type_confidence": self.document_type_confidence,
            "fields": {name: fv.to_dict() for name, fv in self.fields.items()},
            "ocr_text": self.ocr_text,
            "provider": self.provider,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ExtractionResult":
        return ExtractionResult(
            document_type=data["document_type"],
            document_type_confidence=data.get("document_type_confidence"),
            fields={
                name: FieldValue.from_dict(fv)
                for name, fv in data.get("fields", {}).items()
            },
            ocr_text=data.get("ocr_text", ""),
            provider=data.get("provider", "unknown"),
        )
