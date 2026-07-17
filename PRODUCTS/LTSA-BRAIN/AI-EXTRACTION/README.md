# AI Extraction Capability

Product: LTSA-BRAIN
Manufactured under: LTSA-BRAIN Document Upload MVP (Engineering Document Upload Pipeline)

Reusable OCR + AI field-extraction capability, invoked by the LTSA n8n
Document Upload workflow (`BUILD-PACKS/BP-DOCUMENT-EXTRACTION`) via an
Execute Command node calling `cli.py`. Per Chief Architect ruling:

> Claude is the first provider, not the architecture. Keep provider-specific
> code isolated. Return a normalized JSON structure. Make it possible to
> add other providers later without changing the LTSA workflow.

## Shape

- `extraction_provider.py` -- `ExtractionProvider` abstract interface (`extract(file_path, mime_type) -> ExtractionResult`).
- `claude_extraction_provider.py` -- the first (and currently only) provider. All Anthropic-SDK-specific code lives here only; sends the document/image directly to Claude (`claude-opus-4-8`) with a structured-output JSON schema (`output_config.format`) that performs OCR, document-type detection, and field extraction in one call.
- `models.py` -- `ExtractionResult` / `FieldValue`, the normalized shape every provider returns and every caller (the n8n workflow, via `cli.py`'s JSON output) consumes.
- `cli.py` -- the sole integration boundary. `python cli.py <file_path> <mime_type> [--provider claude]` prints the normalized result as one line of JSON to stdout.

## Adding a provider

1. Implement `ExtractionProvider` in a new file (e.g. `azure_extraction_provider.py`).
2. Register it in `cli.py`'s `PROVIDERS` dict.
3. No change to `BUILD-PACKS/BP-DOCUMENT-EXTRACTION`'s n8n workflow is required — it always calls `cli.py` the same way and reads the same normalized JSON shape.

## Scope

Original-file persistence is out of scope for this capability — it reads
the uploaded file from wherever the caller placed it (a temporary path) and
never writes a copy. Physical document storage is deferred to a future
Platform Storage MWO, per Chief Architect ruling.

## Tests

```
pytest PRODUCTS/LTSA-BRAIN/AI-EXTRACTION/TEST
```

`test_claude_extraction_provider.py` mocks `anthropic.Anthropic` — no live
API key or network access is required or used.
