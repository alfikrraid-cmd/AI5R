import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from claude_extraction_provider import ClaudeExtractionProvider
from models import DOCUMENT_TYPES, FIELD_NAMES


def _make_fake_response(document_type: str = "PUMP_DATASHEET") -> SimpleNamespace:
    payload = {
        "document_type": document_type,
        "document_type_confidence": 0.88,
        "ocr_text": "ACME PUMP CO. MODEL X-100 SIZE 4X6-10",
        "fields": {
            name: {"value": None, "confidence": None} for name in FIELD_NAMES
        },
    }
    payload["fields"]["pump_manufacturer"] = {"value": "ACME PUMP CO.", "confidence": 0.97}
    payload["fields"]["pump_model"] = {"value": "X-100", "confidence": 0.93}

    text_block = SimpleNamespace(type="text", text=json.dumps(payload))
    return SimpleNamespace(content=[text_block])


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    file_path = tmp_path / "datasheet.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake pdf bytes for test")
    return file_path


def test_extract_sends_document_block_for_pdf_and_parses_response(tmp_pdf):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _make_fake_response()

    provider = ClaudeExtractionProvider(client=fake_client)
    result = provider.extract(tmp_pdf, "application/pdf")

    assert result.document_type == "PUMP_DATASHEET"
    assert result.document_type_confidence == 0.88
    assert result.provider == "claude"
    assert result.fields["pump_manufacturer"].value == "ACME PUMP CO."
    assert result.fields["pump_manufacturer"].confidence == 0.97
    assert result.fields["seal_manufacturer"].value is None

    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-4-8"
    content_blocks = call_kwargs["messages"][0]["content"]
    assert content_blocks[0]["type"] == "document"
    assert content_blocks[0]["source"]["media_type"] == "application/pdf"
    assert call_kwargs["output_config"]["format"]["type"] == "json_schema"
    schema = call_kwargs["output_config"]["format"]["schema"]
    assert set(schema["properties"]["document_type"]["enum"]) == set(DOCUMENT_TYPES)


def test_extract_sends_image_block_for_png(tmp_path: Path):
    file_path = tmp_path / "nameplate.png"
    file_path.write_bytes(b"fake png bytes")

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _make_fake_response(document_type="NAMEPLATE")

    provider = ClaudeExtractionProvider(client=fake_client)
    result = provider.extract(file_path, "image/png")

    assert result.document_type == "NAMEPLATE"
    call_kwargs = fake_client.messages.create.call_args.kwargs
    content_blocks = call_kwargs["messages"][0]["content"]
    assert content_blocks[0]["type"] == "image"
    assert content_blocks[0]["source"]["media_type"] == "image/png"


def test_extract_rejects_unsupported_mime_type(tmp_path: Path):
    file_path = tmp_path / "doc.txt"
    file_path.write_bytes(b"plain text")

    provider = ClaudeExtractionProvider(client=MagicMock())

    with pytest.raises(ValueError):
        provider.extract(file_path, "text/plain")
