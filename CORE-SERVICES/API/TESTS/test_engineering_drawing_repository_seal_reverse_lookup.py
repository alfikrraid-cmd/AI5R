"""R2B (Mechanical Seal Engineering Drawing + Revision BOM Real Read
Path) -- unit tests for EngineeringDrawingRepository.list_drawings_for_seal(),
the new reverse-lookup method (Seal -> its linked Engineering Drawings).

Deliberately NOT modeled on test_engineering_drawing_repository.py's own
real-Postgres-container pattern: this MWO's own DB rule is explicit --
"DO NOT create PostgreSQL" -- and this workstation has no local Postgres
available at all. A fake DatabaseRunner (duck-typed: only
query_scalar(sql) is ever called by _json_query) proves the exact SQL
this method builds -- target_type/target_code equality, retracted_at
exclusion, and which _drawing_area_scope_clause it delegates to -- and
that rows come back unchanged. It does NOT prove real Postgres rows
exist or that Postgres accepts this SQL; that is RUNTIME_VERIFICATION_REQUIRED,
reported separately, never claimed as PASS here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
for path in (_CORE_SERVICES_DIR,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from API.engineering_drawing_repository import EngineeringDrawingRepository  # noqa: E402


class FakeRunner:
    """Records every SQL string handed to it; returns a canned JSON
    payload as if it were the DB's own response. No connection, no
    Postgres, no docker -- pure Python."""

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.queries: list[str] = []

    def query_scalar(self, sql: str) -> str:
        self.queries.append(sql)
        return json.dumps(self.rows)


def _repo(rows):
    runner = FakeRunner(rows)
    return EngineeringDrawingRepository(runner), runner


def test_queries_exactly_target_type_seal_and_the_given_seal_code():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-101", scope=None)

    sql = runner.queries[-1]
    assert "l.target_type = 'SEAL'" in sql
    assert "l.target_code = 'SC-101'" in sql
    # No other target_type literal is ever compared against -- ASSET/
    # COMPONENT links are excluded by construction, not by a post-filter.
    assert "'ASSET'" not in sql
    assert "'COMPONENT'" not in sql


def test_excludes_retracted_links():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-101", scope=None)

    assert "l.retracted_at IS NULL" in runner.queries[-1]


def test_exact_match_only_no_fuzzy_or_substring_operator():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-101", scope=None)

    sql = runner.queries[-1]
    # Equality only -- never LIKE/ILIKE/~ against target_code or
    # seal_name, matching _validate_target's own write-time discipline
    # (no fuzzy/substring/alias matching anywhere in this domain).
    assert "ILIKE" not in sql
    assert " LIKE " not in sql


def test_a_seal_code_with_a_quote_is_escaped_not_concatenated_raw():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-'; DROP TABLE x; --", scope=None)

    sql = runner.queries[-1]
    # _sql() (this repository's existing escaping helper, used by every
    # other method here) must still be the thing building this literal --
    # a raw single quote must never appear unescaped/unpaired.
    assert sql.count("'") % 2 == 0


def test_unscoped_uses_the_unconditional_scope_clause():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-101", scope=None)

    assert "WHERE l.target_type = 'SEAL'" in runner.queries[-1]
    assert " AND TRUE " in runner.queries[-1] or runner.queries[-1].rstrip().endswith("TRUE")


def test_empty_scope_uses_the_fail_closed_false_clause():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-101", scope=frozenset())

    assert "FALSE" in runner.queries[-1]


def test_restricted_scope_reuses_the_same_asset_link_area_clause_every_other_drawing_route_uses():
    repo, runner = _repo([])
    repo.list_drawings_for_seal("SC-101", scope=frozenset({"AREA-1"}))

    sql = runner.queries[-1]
    # This is the SAME _drawing_area_scope_clause() every other single-
    # drawing route (get_engineering_drawing, list_engineering_drawing_
    # revisions, ...) already applies -- a drawing with ONLY a SEAL link
    # (no ASSET link) resolves to no determinable area and is therefore
    # excluded for a restricted scope. Not overridden or special-cased
    # here for the reverse-lookup path.
    assert "engineering_drawing_link l JOIN asset_registry a" in sql
    assert "'AREA-1'" in sql


def test_returns_rows_from_the_runner_unchanged():
    canned = [{"drawing_code": "DWG-1", "title": "Seal Assembly Drawing"}]
    repo, runner = _repo(canned)

    result = repo.list_drawings_for_seal("SC-101", scope=None)

    assert result == canned


def test_empty_result_is_an_empty_list_not_an_error():
    repo, runner = _repo([])

    result = repo.list_drawings_for_seal("SC-999-NO-DRAWINGS", scope=None)

    assert result == []
