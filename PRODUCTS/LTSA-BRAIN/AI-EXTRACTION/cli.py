"""CLI entry point for the AI Extraction Capability.

This is the sole integration boundary the LTSA n8n workflow calls (via an
Execute Command node) -- the workflow invokes this script with a file path
and mime type and reads the JSON result from stdout. It never imports the
Anthropic SDK directly and never changes when a provider is added, per
Chief Architect ruling: "Make it possible to add other providers later
without changing the LTSA workflow."

Usage:
    python cli.py <file_path> <mime_type> [--provider claude]

Prints one line of JSON (the normalized ExtractionResult, see models.py) to
stdout on success. On failure, prints an error message to stderr and exits
non-zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from extraction_provider import ExtractionProvider

PROVIDERS: dict[str, type[ExtractionProvider]] = {}


def _register_default_providers() -> None:
    if "claude" not in PROVIDERS:
        from claude_extraction_provider import ClaudeExtractionProvider

        PROVIDERS["claude"] = ClaudeExtractionProvider


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Extraction Capability CLI")
    parser.add_argument("file_path", type=Path)
    parser.add_argument("mime_type")
    parser.add_argument("--provider", default="claude", choices=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _register_default_providers()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    provider_cls = PROVIDERS.get(args.provider)
    if provider_cls is None:
        print(
            f"Unknown extraction provider {args.provider!r}. "
            f"Registered providers: {sorted(PROVIDERS)}",
            file=sys.stderr,
        )
        return 1

    if not args.file_path.is_file():
        print(f"File not found: {args.file_path}", file=sys.stderr)
        return 1

    try:
        result = provider_cls().extract(args.file_path, args.mime_type)
    except Exception as exc:  # surfaced to the caller, not swallowed
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
