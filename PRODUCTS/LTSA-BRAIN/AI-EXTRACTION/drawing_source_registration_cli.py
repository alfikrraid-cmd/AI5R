"""CLI for registering a real Engineering Drawing source document
(Drawing-R5A0B). Deliberately a SEPARATE script from cli.py -- that
file's own docstring states it is "the sole integration boundary the
LTSA n8n workflow calls" for the generic Document Upload extraction
pipeline (a different capability/model entirely, see
drawing_extraction_models.py's own "specialization, not a second
generic framework" note); this mirrors resolve_identity_cli.py's own
existing "one script per capability" convention instead of overloading
cli.py's narrow, explicit contract.

Registers a source ONLY. Never stages extraction, never reviews, never
promotes (Section 9's own explicit instruction) -- those remain
separate, deliberate, later actions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_AI_EXTRACTION_DIR = Path(__file__).resolve().parent
_INGESTION_DIR = _AI_EXTRACTION_DIR.parent / "INGESTION"
for _path in (_AI_EXTRACTION_DIR, _INGESTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from knowledge_source_registration_service import KnowledgeSourceRegistrationService  # noqa: E402
from minio_drawing_source_bytes_provider import minio_client_from_env  # noqa: E402

_EXTENSION_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register a real Engineering Drawing source document")
    parser.add_argument("--file", required=True, type=Path, dest="file_path")
    return parser.parse_args(argv)


def _runner_from_env():
    from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner

    return DatabaseRunner(
        DatabaseConfig(
            host=os.environ.get("AI5R_POSTGRES_HOST", "postgres"),
            port=int(os.environ.get("AI5R_POSTGRES_PORT", "5432")),
            user=os.environ["AI5R_POSTGRES_USER"],
            password=os.environ["AI5R_POSTGRES_PASSWORD"],
            database=os.environ["AI5R_LTSA_POSTGRES_DB"],
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if not args.file_path.is_file():
        print(f"File not found: {args.file_path}", file=sys.stderr)
        return 1

    mime_type = _EXTENSION_MIME.get(args.file_path.suffix.lower())
    if mime_type is None:
        print(
            f"Unsupported extension {args.file_path.suffix!r} "
            f"(supported: {sorted(_EXTENSION_MIME)})",
            file=sys.stderr,
        )
        return 1

    file_bytes = args.file_path.read_bytes()
    client, bucket = minio_client_from_env()
    runner = _runner_from_env()
    service = KnowledgeSourceRegistrationService(runner, client, bucket)

    try:
        result = service.register(file_bytes, args.file_path.name, mime_type)
    except Exception as exc:  # surfaced to the caller, not swallowed
        print(f"Registration failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
