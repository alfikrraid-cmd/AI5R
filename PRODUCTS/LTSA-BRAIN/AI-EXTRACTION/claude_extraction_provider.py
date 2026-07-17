"""ClaudeExtractionProvider -- the initial (first) AI Extraction Capability
provider, per Chief Architect ruling on the Document Upload MVP.

Sends the uploaded document directly to Claude as a document/image content
block with a structured-output JSON schema (output_config.format) covering
document-type detection, OCR text, and the Minimum Fields set in a single
call -- no separate OCR engine. All Claude-specific request/response
handling is isolated to this file; nothing outside it references the
Anthropic SDK, so a future provider can be added by implementing
ExtractionProvider without touching the LTSA workflow.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import anthropic

from extraction_provider import ExtractionProvider
from models import DOCUMENT_TYPES, FIELD_NAMES, ExtractionResult, FieldValue

_MODEL = "claude-opus-4-8"

_SYSTEM_PROMPT = (
    "You are an engineering document analyst for an industrial asset "
    "reliability platform. You are given a scanned engineering document "
    "(a pump datasheet, a mechanical seal installation report, an "
    "engineering drawing, or an equipment nameplate). Read the document, "
    "classify its type, transcribe its visible text, and extract the "
    "listed fields. If a field is not present on this document type or is "
    "not legible, set its value to null and its confidence to null. Set "
    "confidence between 0 and 1, reflecting how certain you are the "
    "transcribed value is correct."
)

_FIELD_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"anyOf": [{"type": "string"}, {"type": "number"}, {"type": "null"}]},
        "confidence": {"anyOf": [{"type": "number"}, {"type": "null"}]},
    },
    "required": ["value", "confidence"],
    "additionalProperties": False,
}

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": list(DOCUMENT_TYPES)},
        "document_type_confidence": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "ocr_text": {"type": "string"},
        "fields": {
            "type": "object",
            "properties": {name: _FIELD_ENTRY_SCHEMA for name in FIELD_NAMES},
            "required": list(FIELD_NAMES),
            "additionalProperties": False,
        },
    },
    "required": ["document_type", "document_type_confidence", "ocr_text", "fields"],
    "additionalProperties": False,
}

_MIME_TO_IMAGE_TYPE = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
}


class ClaudeExtractionProvider(ExtractionProvider):
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    def extract(self, file_path: Path, mime_type: str) -> ExtractionResult:
        content_block = self._build_content_block(file_path, mime_type)

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=8000,
            system=_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
                        {
                            "type": "text",
                            "text": (
                                "Classify this document, transcribe its text, and "
                                "extract the requested fields."
                            ),
                        },
                    ],
                }
            ],
        )

        text_block = next(block for block in response.content if block.type == "text")
        parsed = json.loads(text_block.text)

        fields = {
            name: FieldValue(value=entry.get("value"), confidence=entry.get("confidence"))
            for name, entry in parsed["fields"].items()
        }

        return ExtractionResult(
            document_type=parsed["document_type"],
            document_type_confidence=parsed.get("document_type_confidence"),
            fields=fields,
            ocr_text=parsed.get("ocr_text", ""),
            provider="claude",
        )

    @staticmethod
    def _build_content_block(file_path: Path, mime_type: str) -> dict:
        data = base64.standard_b64encode(file_path.read_bytes()).decode("utf-8")

        if mime_type == "application/pdf":
            return {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": data},
            }

        image_media_type = _MIME_TO_IMAGE_TYPE.get(mime_type)
        if image_media_type is None:
            raise ValueError(
                f"ClaudeExtractionProvider does not support mime_type={mime_type!r}; "
                "expected application/pdf, image/jpeg, or image/png"
            )

        return {
            "type": "image",
            "source": {"type": "base64", "media_type": image_media_type, "data": data},
        }
