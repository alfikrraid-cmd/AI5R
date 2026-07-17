import json
from pathlib import Path

import pytest

import cli
from models import ExtractionResult, FieldValue


class _FakeProvider:
    def extract(self, file_path: Path, mime_type: str) -> ExtractionResult:
        return ExtractionResult(
            document_type="NAMEPLATE",
            document_type_confidence=0.75,
            fields={"customer": FieldValue(value="ACME CO.", confidence=0.8)},
            ocr_text="ACME CO.",
            provider="fake",
        )


@pytest.fixture(autouse=True)
def register_fake_provider():
    cli.PROVIDERS["fake"] = _FakeProvider
    yield
    cli.PROVIDERS.pop("fake", None)


def test_cli_prints_normalized_json_on_success(tmp_path: Path, capsys):
    file_path = tmp_path / "nameplate.jpg"
    file_path.write_bytes(b"fake jpeg bytes")

    exit_code = cli.main([str(file_path), "image/jpeg", "--provider", "fake"])

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["document_type"] == "NAMEPLATE"
    assert printed["fields"]["customer"]["value"] == "ACME CO."


def test_cli_fails_cleanly_for_missing_file(tmp_path: Path, capsys):
    missing = tmp_path / "does-not-exist.pdf"

    exit_code = cli.main([str(missing), "application/pdf", "--provider", "fake"])

    assert exit_code == 1
    assert "not found" in capsys.readouterr().err.lower()


def test_cli_fails_cleanly_for_unknown_provider(tmp_path: Path, capsys):
    file_path = tmp_path / "doc.pdf"
    file_path.write_bytes(b"fake pdf bytes")

    exit_code = cli.main([str(file_path), "application/pdf", "--provider", "nonexistent"])

    assert exit_code == 1
    assert "unknown extraction provider" in capsys.readouterr().err.lower()
