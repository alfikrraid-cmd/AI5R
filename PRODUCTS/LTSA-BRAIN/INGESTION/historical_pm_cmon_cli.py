"""MWO-LTSA-HISTORICAL-JULY-PROMOTION-PREPROD-CLOSURE-001 -- the smallest
possible production-usable CLI wrapper around the EXISTING historical
PM/CMON/Finding ingestion functions (register_source_document(),
build_area_dry_run(), stage_area_candidates()). No new ingestion logic,
no new matching/classification rule, no promote path -- promotion stays
a deliberate separate, human-reviewed step through the existing
Historical Review UI/API (routers/historical_review.py), never
automatic here.

Reuses PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_pump_inventory_db_upsert.py's
own established CLI conventions verbatim (DatabaseConfig/DatabaseRunner,
--env-file/--compose-file, and -- most importantly -- its exact
"refuse to write against an unconfigured/default database target"
safety gate): `stage` (the only mode that writes) refuses to run unless
the caller passed an explicit --database or set AI5R_LTSA_POSTGRES_DB,
printing the resolved target before doing anything. `dry-run` is always
safe (zero-write) and never requires that guard.

Canonical pump tags are read live from the resolved database's
ltsa_pumps table (same `SELECT tag_number FROM ltsa_pumps` query
ltsa_hoc_pm_cm_db_upsert.py::load_state() already uses) -- never
hardcoded, never guessed.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

from historical_pm_cmon_orchestrator import (
    build_area_dry_run,
    register_source_document,
    stage_area_candidates,
)
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _extra in (_REPO_ROOT / "CORE-SERVICES", _REPO_ROOT / "AI5R-SDK"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from API.historical_pm_cmon_staging_repository import HistoricalPMCMONStagingRepository  # noqa: E402


def _print_counts(label: str, result) -> None:
    print(f"{label}: PM={len(result.pm_candidates)} CMON={len(result.cmon_candidates)} "
          f"Finding={len(result.finding_candidates)} "
          f"(total={len(result.pm_candidates) + len(result.cmon_candidates) + len(result.finding_candidates)})",
          file=sys.stderr)
    if result.critical_missing:
        print(f"  critical_missing: {len(result.critical_missing)} item(s) -- e.g. {result.critical_missing[0]!r}",
              file=sys.stderr)


def _resolve_database(args: argparse.Namespace) -> tuple[str, str]:
    env_database = os.getenv("AI5R_LTSA_POSTGRES_DB")
    database = args.database or env_database or DatabaseConfig.database
    source = "--database" if args.database else ("AI5R_LTSA_POSTGRES_DB" if env_database else "default")
    return database, source


def _build_config(args: argparse.Namespace, database: str) -> DatabaseConfig:
    # Mirrors CORE-SERVICES/BACKEND-API/dependencies.py::_resolve_import_
    # database_config() verbatim (same env var names, same direct-connect-
    # if-AI5R_POSTGRES_HOST-else-docker-exec precedence) -- the real
    # backend's own DB resolution, reused rather than a third convention.
    direct_host = os.getenv("AI5R_POSTGRES_HOST")
    if direct_host:
        return DatabaseConfig(
            host=direct_host,
            port=int(os.getenv("AI5R_POSTGRES_PORT", "5432")),
            user=os.getenv("AI5R_POSTGRES_USER", "ai5r"),
            password=os.getenv("AI5R_POSTGRES_PASSWORD", ""),
            database=database,
        )
    return DatabaseConfig(env_file=args.env_file, compose_file=args.compose_file, database=database)


def _fetch_canonical_pump_tags(runner: DatabaseRunner) -> set[str]:
    rows = _json_query("SELECT tag_number FROM ltsa_pumps", runner)
    return {r["tag_number"] for r in rows}


def _build_result(args: argparse.Namespace, runner: DatabaseRunner):
    source = register_source_document(Path(args.pdf), Path(args.xlsx), area_label=args.area)
    canonical_pump_tags = _fetch_canonical_pump_tags(runner)
    print(f"Canonical pump roster loaded from DB: {len(canonical_pump_tags)} tags", file=sys.stderr)
    known_hashes = {
        r["file_hash"] for r in _json_query(
            "SELECT file_hash FROM pdf_document UNION SELECT file_hash FROM knowledge_source_registry", runner
        )
    } if args.check_duplicates else frozenset()
    return source, build_area_dry_run(source, canonical_pump_tags=canonical_pump_tags, known_source_hashes=known_hashes)


def cmd_dry_run(args: argparse.Namespace) -> int:
    database, source_kind = _resolve_database(args)
    print(f"Target database: {database} (source: {source_kind}) -- READ-ONLY", file=sys.stderr)
    runner = DatabaseRunner(_build_config(args, database))
    _source, result = _build_result(args, runner)
    _print_counts("DRY RUN (zero-write)", result)
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    database, source_kind = _resolve_database(args)
    if source_kind == "default":
        print(
            "Refusing to stage with no explicit database target: pass --database "
            "or set AI5R_LTSA_POSTGRES_DB. (Currently would default to "
            f"'{database}', which is almost never the intended LTSA database.)",
            file=sys.stderr,
        )
        return 1
    print(f"Target database: {database} (source: {source_kind}) -- WRITE (staging only, never promotes)", file=sys.stderr)
    runner = DatabaseRunner(_build_config(args, database))

    source, result = _build_result(args, runner)
    _print_counts("PREFLIGHT (before staging)", result)

    if not args.yes:
        print("Re-run with --yes to actually stage these candidates. No write has occurred.", file=sys.stderr)
        return 0

    staging = HistoricalPMCMONStagingRepository(runner)
    pdf_document_id = args.pdf_document_id or f"PDF-{uuid.uuid4().hex[:12].upper()}"
    staged = stage_area_candidates(result, staging_repository=staging, source_document_id=pdf_document_id)
    print(f"STAGED: {len(staged)} candidate(s) under source_document_id={pdf_document_id!r} "
          f"(source xlsx_sha256={source.xlsx_sha256})", file=sys.stderr)
    print("No promotion occurred -- review via the Historical Review UI/API before any promote action.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Historical PM/CMON/Finding ingestion: dry-run (zero-write) or stage "
        "(writes to document_field_extraction only -- never promotes)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn in (("dry-run", cmd_dry_run), ("stage", cmd_stage)):
        p = sub.add_parser(name)
        p.add_argument("--pdf", required=True, type=Path)
        p.add_argument("--xlsx", required=True, type=Path)
        p.add_argument("--area", required=True, help="Area label, e.g. HOC/HSC/HCC/OM_UTL")
        p.add_argument("--env-file", type=Path, default=None)
        p.add_argument("--compose-file", type=Path, default=None)
        p.add_argument("--database", default=None, help="Target Postgres database. Defaults to "
                        "AI5R_LTSA_POSTGRES_DB if set, else DatabaseConfig's own default.")
        p.add_argument("--check-duplicates", action="store_true",
                        help="Skip EXACT_DUPLICATE candidates already known to pdf_document/knowledge_source_registry.")
        p.set_defaults(func=fn)

    stage_parser = [a for a in sub.choices.values() if a.get_default("func") is cmd_stage][0]
    stage_parser.add_argument("--yes", action="store_true", help="Actually write staged candidates (omit for a preflight-only pass).")
    stage_parser.add_argument("--pdf-document-id", default=None, help="Existing pdf_document.pdf_document_id to attribute staged rows to.")

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
