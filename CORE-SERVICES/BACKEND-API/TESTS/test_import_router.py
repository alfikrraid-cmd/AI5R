import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

_REPO_ROOT = BACKEND_API_DIR.parents[1]
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from main import app
from dependencies import get_import_database_runner, get_import_session_repository
from API.conflict_resolution import build_conflict_report as _build_conflict_report
from API.import_session import build_canonical_packages, build_import_session
from API.import_session_repository import ImportSessionRepository
from API.import_validator import ImportPackage, parse_import_package, validate_import_package
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query

client = TestClient(app)

_RUNTIME_DIR = _REPO_ROOT / "CORE-SERVICES" / "RUNTIME"


def _real_runner() -> DatabaseRunner:
    return DatabaseRunner(
        DatabaseConfig(env_file=_RUNTIME_DIR / ".env.verify.local", compose_file=_RUNTIME_DIR / "compose.yaml")
    )


def _pump_present(runner: DatabaseRunner, tag_number: str) -> bool:
    rows = _json_query(f"SELECT tag_number FROM ltsa_pumps WHERE tag_number = '{tag_number}'", runner)
    return rows != []


@pytest.fixture
def real_db_cleanup():
    """Only used by the MWO-LTSA-103 real-execution tests below -- every
    other test in this file stays in-memory (no live DB), matching this
    file's own pre-existing convention. TEST-ROUTER-* namespaced, deleted
    before and after."""
    runner = _real_runner()
    runner.execute_script("DELETE FROM ltsa_pumps WHERE tag_number LIKE 'TEST-ROUTER-%';")
    yield runner
    runner.execute_script("DELETE FROM ltsa_pumps WHERE tag_number LIKE 'TEST-ROUTER-%';")

# Import API Foundation -- router only: every route delegates to
# API.import_validator.validate_import_package / API.conflict_resolution.
# build_conflict_report / API.import_session.build_import_session
# unmodified. These tests prove wiring/serialization/DI, not validation
# rules themselves (those already have their own unit test files:
# TESTS/test_import_validator.py, TESTS/test_conflict_resolution.py,
# TESTS/test_import_session.py).


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


VALID_PUMP = {"tag_number": "P-101", "area": "Unit 1"}
VALID_SEAL = {"seal_code": "SC-001", "seal_name": "John Crane Type 21"}
VALID_INSTALLATION = {
    "installation_code": "INSTL-001",
    "report_no": "001/INSTL/2026",
    "source_document_name": "Install Report.pdf",
}
VALID_DOCUMENT = {
    "document_code": "DOC-001",
    "seal_code": "SC-001",
    "document_type": "DRAWING",
    "title": "SC-001 GA Drawing",
}


# --- OpenAPI registration -----------------------------------------------


def test_all_five_routes_are_registered_in_openapi():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/import/validate" in paths
    assert "/api/ltsa/import/conflicts" in paths
    assert "/api/ltsa/import/session" in paths
    assert "/api/ltsa/import/execute" in paths
    assert "/api/ltsa/import/status/{session_id}" in paths
    assert set(paths["/api/ltsa/import/validate"]) == {"post"}
    assert set(paths["/api/ltsa/import/conflicts"]) == {"post"}
    assert set(paths["/api/ltsa/import/session"]) == {"post"}
    assert set(paths["/api/ltsa/import/execute"]) == {"post"}
    assert set(paths["/api/ltsa/import/status/{session_id}"]) == {"get"}


# --- validate endpoint ----------------------------------------------------


def test_validate_endpoint_returns_valid_summary_for_a_clean_package():
    response = client.post(
        "/api/ltsa/import/validate",
        json={"pumps": [VALID_PUMP], "seals": [], "installations": [], "documents": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["summary"]["pump_count"] == 1
    assert body["data"]["summary"]["is_valid"] is True
    assert body["data"]["errors"] == []


def test_validate_endpoint_reports_structural_errors_for_missing_required_field():
    response = client.post(
        "/api/ltsa/import/validate",
        json={"pumps": [{"tag_number": "P-101"}], "seals": [], "installations": [], "documents": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["summary"]["is_valid"] is False
    assert body["data"]["errors"][0]["code"] == "MISSING_REQUIRED_FIELD"
    assert body["data"]["errors"][0]["field"] == "area"


def test_validate_endpoint_defaults_missing_entity_lists_to_empty():
    response = client.post("/api/ltsa/import/validate", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["summary"]["pump_count"] == 0
    assert body["data"]["summary"]["is_valid"] is True


# --- conflicts endpoint -----------------------------------------------------


def test_conflicts_endpoint_flags_a_new_entity_as_create_new():
    response = client.post(
        "/api/ltsa/import/conflicts",
        json={
            "database_snapshot": {"pumps": [], "seals": [], "installations": [], "documents": []},
            "incoming_package": {"pumps": [VALID_PUMP], "seals": [], "installations": [], "documents": []},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["create_new_count"] == 1
    assert body["data"]["conflicts"][0]["resolution"] == "CREATE_NEW"


def test_conflicts_endpoint_flags_a_real_value_disagreement_as_manual_review():
    response = client.post(
        "/api/ltsa/import/conflicts",
        json={
            "database_snapshot": {"pumps": [{"tag_number": "P-101", "area": "Unit 1"}], "seals": [], "installations": [], "documents": []},
            "incoming_package": {"pumps": [{"tag_number": "P-101", "area": "Unit 2"}], "seals": [], "installations": [], "documents": []},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["manual_review_count"] == 1
    assert body["data"]["conflicts"][0]["resolution"] == "MANUAL_REVIEW"


def test_conflicts_endpoint_returns_no_conflicts_for_identical_packages():
    package = {"pumps": [VALID_PUMP], "seals": [], "installations": [], "documents": []}
    response = client.post(
        "/api/ltsa/import/conflicts",
        json={"database_snapshot": package, "incoming_package": package},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["has_conflicts"] is False
    assert body["data"]["conflicts"] == []


# --- session endpoint --------------------------------------------------------


def test_session_endpoint_builds_and_returns_a_new_import_session():
    response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-001",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "created_by": "engineer@ai5r",
            "package": {"pumps": [VALID_PUMP], "seals": [], "installations": [], "documents": []},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session_id"] == "SESS-001"
    assert body["data"]["status"] == "NEW"
    assert body["data"]["statistics"]["total_packages"] == 1
    assert body["data"]["statistics"]["valid_packages"] == 1


def test_session_endpoint_rejects_a_status_outside_the_closed_vocabulary():
    # build_import_session() raises ValueError for a status outside
    # IMPORT_SESSION_STATUSES (reused unmodified) -- TestClient re-raises
    # unhandled exceptions rather than converting them to a response,
    # proving the route performs no silent normalization/invention of its
    # own status vocabulary.
    with pytest.raises(ValueError, match="NOT_A_REAL_STATUS"):
        client.post(
            "/api/ltsa/import/session",
            json={
                "session_id": "SESS-002",
                "created_at": "2026-08-12T00:00:00Z",
                "source": "manual-upload",
                "status": "NOT_A_REAL_STATUS",
                "package": {"pumps": [], "seals": [], "installations": [], "documents": []},
            },
        )


# --- status endpoint ------------------------------------------------------


def test_status_endpoint_returns_a_session_previously_created_via_session_endpoint():
    client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-003",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "VALIDATED",
            "package": {"pumps": [VALID_PUMP], "seals": [], "installations": [], "documents": []},
        },
    )

    response = client.get("/api/ltsa/import/status/SESS-003")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session_id"] == "SESS-003"
    assert body["data"]["status"] == "VALIDATED"


def test_status_endpoint_reports_not_found_for_an_unknown_session_id():
    response = client.get("/api/ltsa/import/status/UNKNOWN-SESSION")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None


# --- execute endpoint (MWO-LTSA-103 -- real, wired to ImportExecutionEngine) ---


def test_execute_endpoint_reports_session_not_found_for_an_unknown_session_id():
    response = client.post("/api/ltsa/import/execute", json={"session_id": "UNKNOWN-SESSION"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "not found" in body["message"]


# MWO-LTSA-103A -- POST .../session now computes and stores a real
# ConflictReport too (against payload.database_snapshot, defaulting to an
# empty package when the caller supplies none). This is the mission's own
# explicit deliverable: "After POST /session -> POST /execute must succeed
# without test fixture" -- proven here through the app's own real,
# default-wired ImportSessionRepository AND DatabaseRunner (dependencies.py
# singletons, no Depends() override of either), the public HTTP contract
# only. TEST-ROUTER-* namespaced and cleaned up (real_db_cleanup) since
# this is now a genuine write, unlike every POST .../session-only test
# above it.
def test_session_then_execute_succeeds_end_to_end_through_the_public_api_with_no_test_fixture(real_db_cleanup):
    session_response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-103A-1",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "APPROVED",
            "package": {
                "pumps": [{"tag_number": "TEST-ROUTER-P-103A", "area": "Unit 1"}],
                "seals": [],
                "installations": [],
                "documents": [],
            },
        },
    )
    assert session_response.status_code == 200
    session_body = session_response.json()
    assert session_body["success"] is True
    # The stored session already carries a real conflict_report -- every
    # incoming record resolves CREATE_NEW against the (default, empty)
    # database_snapshot, exactly like POST .../conflicts would report for
    # the same inputs.
    assert session_body["data"]["conflict_report"]["conflict_count"] == 1
    assert session_body["data"]["conflict_report"]["create_new_count"] == 1

    execute_response = client.post("/api/ltsa/import/execute", json={"session_id": "SESS-103A-1"})

    assert execute_response.status_code == 200
    execute_body = execute_response.json()
    assert execute_body["success"] is True
    assert execute_body["data"]["status"] == "COMMITTED"
    assert execute_body["data"]["statistics"]["pump"]["inserted"] == 1

    status_response = client.get("/api/ltsa/import/status/SESS-103A-1")
    assert status_response.json()["data"]["status"] == "IMPORTED"

    live = _json_query("SELECT tag_number FROM ltsa_pumps WHERE tag_number = 'TEST-ROUTER-P-103A'", real_db_cleanup)
    assert live == [{"tag_number": "TEST-ROUTER-P-103A"}]


def test_session_endpoint_uses_the_supplied_database_snapshot_to_compute_real_conflicts():
    response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-103A-2",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "package": {"pumps": [{"tag_number": "P-DUP", "area": "Unit 2"}], "seals": [], "installations": [], "documents": []},
            "database_snapshot": {
                "pumps": [{"tag_number": "P-DUP", "area": "Unit 1"}], "seals": [], "installations": [], "documents": [],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    report = body["data"]["conflict_report"]
    assert report["conflict_count"] == 1
    assert report["conflicts"][0]["resolution"] == "MANUAL_REVIEW"
    assert report["conflicts"][0]["field"] == "area"


def test_session_endpoint_with_no_database_snapshot_supplied_defaults_to_empty():
    response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-103A-3",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "package": {"pumps": [], "seals": [], "installations": [], "documents": []},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["conflict_report"]["conflict_count"] == 0


def _session_ready_for_execution(tag_number: str, runner: DatabaseRunner):
    """A real session with exactly one validated CanonicalKnowledgePackage-
    bearing package and a real conflict_report -- what POST .../session
    itself cannot build today (see this file's own MWO-LTSA-103 comment
    above), constructed directly here as real test setup, the same way
    test_import_worker.py's own _ready_session() helper already does."""
    incoming = ImportPackage(pumps=({"tag_number": tag_number, "area": "Unit 1"},), seals=(), installations=(), documents=())
    validated = validate_import_package(incoming)
    empty_snapshot = parse_import_package({})
    conflicts = _build_conflict_report(empty_snapshot, incoming)
    canonical_packages = build_canonical_packages(incoming)
    return build_import_session(
        session_id=f"SESS-EXEC-{tag_number}",
        created_at="2026-08-12T00:00:00Z",
        source="test-suite",
        status="APPROVED",
        packages=canonical_packages,
        validations=(validated,),
        conflict_report=conflicts,
    )


def test_execute_endpoint_runs_the_real_execution_engine_and_writes_to_the_database(real_db_cleanup):
    runner = real_db_cleanup
    session = _session_ready_for_execution("TEST-ROUTER-P-1", runner)

    repository = ImportSessionRepository()
    repository.create(session)
    app.dependency_overrides[get_import_session_repository] = lambda: repository
    app.dependency_overrides[get_import_database_runner] = lambda: runner

    response = client.post("/api/ltsa/import/execute", json={"session_id": session.session_id})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "COMMITTED"
    assert body["data"]["statistics"]["pump"]["inserted"] == 1

    # The session the repository holds was really advanced, not just the
    # response body -- proves ImportWorker's own "Update Session" step ran.
    updated_session = repository.get(session.session_id)
    assert updated_session.status == "IMPORTED"

    live = _json_query(f"SELECT tag_number FROM ltsa_pumps WHERE tag_number = 'TEST-ROUTER-P-1'", runner)
    assert live == [{"tag_number": "TEST-ROUTER-P-1"}]


def test_execute_endpoint_uses_the_real_database_runner_by_default_without_an_override(real_db_cleanup):
    # No get_import_database_runner override this time -- proves the app
    # wires a real DatabaseRunner via dependencies.py (MWO-LTSA-103), not
    # only ever a test-supplied one.
    runner = real_db_cleanup
    session = _session_ready_for_execution("TEST-ROUTER-P-2", runner)

    repository = ImportSessionRepository()
    repository.create(session)
    app.dependency_overrides[get_import_session_repository] = lambda: repository

    response = client.post("/api/ltsa/import/execute", json={"session_id": session.session_id})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "COMMITTED"
    live = _json_query(f"SELECT tag_number FROM ltsa_pumps WHERE tag_number = 'TEST-ROUTER-P-2'", runner)
    assert live == [{"tag_number": "TEST-ROUTER-P-2"}]


# --- invalid request ------------------------------------------------------


def test_conflicts_endpoint_rejects_a_request_missing_incoming_package():
    response = client.post(
        "/api/ltsa/import/conflicts",
        json={"database_snapshot": {"pumps": [], "seals": [], "installations": [], "documents": []}},
    )

    assert response.status_code == 422


def test_session_endpoint_rejects_a_request_missing_session_id():
    response = client.post(
        "/api/ltsa/import/session",
        json={
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "package": {"pumps": [], "seals": [], "installations": [], "documents": []},
        },
    )

    assert response.status_code == 422


# --- dependency injection --------------------------------------------------


class FakeImportSessionRepository:
    def __init__(self):
        self.saved = []
        self.get_calls = []

    def save(self, session):
        self.saved.append(session)

    def get(self, session_id):
        self.get_calls.append(session_id)
        return self.saved[-1] if self.saved else None


def test_session_and_status_endpoints_use_the_injected_repository_not_a_hardcoded_one():
    fake = FakeImportSessionRepository()
    app.dependency_overrides[get_import_session_repository] = lambda: fake

    create_response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-DI",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "package": {"pumps": [], "seals": [], "installations": [], "documents": []},
        },
    )
    status_response = client.get("/api/ltsa/import/status/SESS-DI")

    assert create_response.status_code == 200
    assert len(fake.saved) == 1
    assert fake.saved[0].session_id == "SESS-DI"
    assert status_response.json()["data"]["session_id"] == "SESS-DI"
    assert fake.get_calls == ["SESS-DI"]


def test_get_import_session_repository_returns_a_real_repository_by_default():
    # No override: proves the app wires a real ImportSessionRepository via
    # dependencies.py, not a global singleton constructed inside the router.
    repository = get_import_session_repository()
    assert isinstance(repository, ImportSessionRepository)


# --- serialization ----------------------------------------------------------


def test_validate_endpoint_serializes_relationships_and_warnings():
    response = client.post(
        "/api/ltsa/import/validate",
        json={
            "pumps": [],
            "seals": [VALID_SEAL],
            "installations": [
                {
                    "installation_code": "INSTL-001",
                    "report_no": "001/INSTL/2026",
                    "source_document_name": "Install Report.pdf",
                    "plant_equip_no": "P-999",
                }
            ],
            "documents": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    relationship = next(
        r for r in body["data"]["relationships"] if r["field"] == "plant_equip_no"
    )
    assert relationship["resolved"] is False
    assert relationship["to_entity_id"] == "P-999"
    warning = next(w for w in body["data"]["warnings"] if w["code"] == "MISSING_PUMP")
    assert warning["entity_id"] == "INSTL-001"


# --- MWO-LTSA-102B -- POST .../session stores real CanonicalKnowledgePackage ---


def test_session_endpoint_stores_real_canonical_knowledge_packages_not_raw_import_package():
    # Before MWO-LTSA-102B this handler stored the raw, plural ImportPackage
    # (`{"pumps": [...], "seals": [...], ...}`) into session.packages, a
    # real type-contract violation (ImportSession.packages is declared
    # tuple[CanonicalKnowledgePackage, ...]). This proves the fix: the
    # stored shape is now genuinely CanonicalKnowledgePackage-shaped
    # (singular "pump"/"seal"/"installation" keys, never "pumps"/"seals").
    response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-CANON-1",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "package": {
                "pumps": [VALID_PUMP, {"tag_number": "P-102", "area": "Unit 2"}],
                "seals": [VALID_SEAL],
                "installations": [],
                "documents": [],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    packages = body["data"]["packages"]

    # One CanonicalKnowledgePackage per entity (2 pumps + 1 seal), not one
    # raw ImportPackage.
    assert len(packages) == 3
    for package in packages:
        assert "pumps" not in package and "seals" not in package
        assert set(package) >= {"pump", "seal", "installation", "drawing", "documents"}

    pump_tags = {p["pump"]["tag_number"] for p in packages if p["pump"]}
    assert pump_tags == {"P-101", "P-102"}
    seal_codes = {p["seal"]["seal_code"] for p in packages if p["seal"]}
    assert seal_codes == {"SC-001"}

    # validated_packages stays exactly one (per incoming batch as a whole),
    # independent of how many CanonicalKnowledgePackage entities packages
    # now holds -- MWO-LTSA-102B removed the old equal-length requirement.
    assert len(body["data"]["validated_packages"]) == 1
    assert body["data"]["statistics"]["total_packages"] == 1


def test_session_endpoint_discloses_a_field_missing_only_from_knowledge_manufacturings_own_validator():
    # A pump missing `tag_number` entirely passes neither validator (both
    # require it), but this specifically proves build_canonical_packages()'s
    # own ManufacturingValidationError is caught and reported gracefully
    # (success: false), never an unhandled 500.
    response = client.post(
        "/api/ltsa/import/session",
        json={
            "session_id": "SESS-CANON-2",
            "created_at": "2026-08-12T00:00:00Z",
            "source": "manual-upload",
            "status": "NEW",
            "package": {"pumps": [{"area": "Unit 1"}], "seals": [], "installations": [], "documents": []},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "tag_number" in body["message"]
    assert body["data"] is None


# --- Pump Master XLSX dry-run (MWO-LTSA-DATA-IMPORT-UI-001B) ---------------
#
# Real Postgres throughout (this file's own established convention), a
# real .xlsx built with openpyxl (the same library ExcelReader itself
# uses), uploaded as a genuine multipart file via TestClient's own `files=`
# -- no mocked adapter, no stubbed dry_run_import.

from io import BytesIO  # noqa: E402

from openpyxl import Workbook  # noqa: E402

_MASTER_PUMP_HEADERS = ("Pump ID", "Tag Number", "Area", "Pump Type", "API Plan", "Notes")


def _master_pump_xlsx_bytes(rows: tuple[tuple, ...]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    worksheet = workbook.create_sheet("Master Pump")
    worksheet.append(_MASTER_PUMP_HEADERS)
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _upload_pump_xlsx(rows: tuple[tuple, ...], filename: str = "master.xlsx"):
    content = _master_pump_xlsx_bytes(rows)
    return client.post(
        "/api/ltsa/import/pump-xlsx/dry-run",
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def test_pump_xlsx_dry_run_uploads_and_analyzes_a_real_workbook():
    response = _upload_pump_xlsx((("PUMP-1", "TEST-ROUTER-P-1A", "Unit 1", "OH", "11/61", None),))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["sheet"] == "Master Pump"
    assert data["source_count"] == 1
    assert data["normalized_count"] == 1
    assert data["new_count"] == 1
    assert data["approval_ready"] is True
    assert data["preview_rows"] == [
        {"tag_number": "TEST-ROUTER-P-1A", "area": "Unit 1", "pump_type": "OH", "api_plan": "11/61", "notes": None}
    ]


def test_pump_xlsx_dry_run_rejects_an_invalid_extension_without_a_crash():
    response = client.post(
        "/api/ltsa/import/pump-xlsx/dry-run",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert ".txt" in body["message"]
    assert body["data"] is None


def test_pump_xlsx_dry_run_rejects_a_corrupt_workbook_as_an_honest_failure_not_a_500():
    response = client.post(
        "/api/ltsa/import/pump-xlsx/dry-run",
        files={"file": ("broken.xlsx", b"not a real workbook", "application/octet-stream")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None


def test_pump_xlsx_dry_run_writes_nothing_to_the_database(real_db_cleanup):
    runner = _real_runner()
    before = _json_query("SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number LIKE 'TEST-ROUTER-%'", runner)

    response = _upload_pump_xlsx(
        (
            ("PUMP-1", "TEST-ROUTER-P-ZW-1", "Unit 1", "OH", "11/61", None),
            ("PUMP-2", "TEST-ROUTER-P-ZW-2", "Unit 1", "BB", "32/62", None),
        )
    )
    assert response.json()["success"] is True

    after = _json_query("SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number LIKE 'TEST-ROUTER-%'", runner)
    assert before == after


def test_pump_xlsx_dry_run_shows_insert_update_and_skip_classification(real_db_cleanup):
    runner = _real_runner()
    # Blank pump_type/api_plan on the DB side (a real gap the incoming row
    # fills) -> USE_IMPORT -> UPDATE. A real, DIFFERENT value on both sides
    # is MANUAL_REVIEW instead (no actionable field), not UPDATE -- see
    # conflict_resolution.py's own resolution rule.
    runner.execute_script("INSERT INTO ltsa_pumps (tag_number, area) VALUES ('TEST-ROUTER-P-UPD', 'Unit 1');")
    runner.execute_script(
        "INSERT INTO ltsa_pumps (tag_number, area, pump_type, api_plan) "
        "VALUES ('TEST-ROUTER-P-SAME', 'Unit 1', 'OH', '11/61');"
    )

    response = _upload_pump_xlsx(
        (
            ("PUMP-1", "TEST-ROUTER-P-NEW", "Unit 1", "OH", "11/61", None),
            ("PUMP-2", "TEST-ROUTER-P-UPD", "Unit 1", "OH", "11/61", None),
            ("PUMP-3", "TEST-ROUTER-P-SAME", "Unit 1", "OH", "11/61", None),
        )
    )

    data = response.json()["data"]
    assert data["new_count"] == 1
    assert data["update_count"] == 1
    assert data["duplicate_count"] == 1


def test_pump_xlsx_dry_run_rejects_a_row_with_a_missing_required_field_and_shows_it_in_row_issues():
    response = _upload_pump_xlsx((("PUMP-1", "TEST-ROUTER-P-NOAREA", None, "OH", "11/61", None),))

    data = response.json()["data"]
    assert data["rejected_count"] == 1
    assert data["approval_ready"] is False
    assert data["row_issues"][0]["code"] == "MISSING_REQUIRED_FIELD"
    assert data["row_issues"][0]["entity_id"] == "TEST-ROUTER-P-NOAREA"


def test_pump_xlsx_dry_run_preserves_ab_and_arbr_as_distinct_pumps():
    response = _upload_pump_xlsx(
        (
            ("PUMP-1", "TEST-ROUTER-P-13A", "Unit 1", "BB", "32/62", None),
            ("PUMP-2", "TEST-ROUTER-P-13AR", "Unit 1", "BB", "32/62", None),
            ("PUMP-3", "TEST-ROUTER-P-13B", "Unit 1", "BB", "32/62", None),
            ("PUMP-4", "TEST-ROUTER-P-13BR", "Unit 1", "BB", "32/62", None),
        )
    )

    data = response.json()["data"]
    assert data["normalized_count"] == 4
    assert data["new_count"] == 4


def test_pump_xlsx_dry_run_is_deterministic_across_repeated_calls():
    rows = (("PUMP-1", "TEST-ROUTER-P-DET", "Unit 1", "OH", "11/61", None),)

    first = _upload_pump_xlsx(rows).json()["data"]
    second = _upload_pump_xlsx(rows).json()["data"]

    # session_id (fresh uuid per call) and source (a fresh random temp-file
    # path per upload, deleted after each request -- see the endpoint's own
    # "Temporary file lifecycle" note) legitimately differ per call; every
    # other field -- the real classification/counts/issues -- must not.
    for report in (first, second):
        report.pop("session_id")
        report.pop("source")
    assert first == second


# --- Dry-run -> persisted session -> Approve -> execute (MWO-LTSA-DATA-IMPORT-UI-001C) ---
#
# Real Postgres throughout, real multipart upload, real POST .../execute --
# no mocked adapter, no stubbed dry_run_import/execute_import. TEST-ROUTER-
# namespaced, cleaned by the same real_db_cleanup fixture every other real-
# write test in this file already uses.


def _dry_run_data(rows: tuple[tuple, ...], filename: str = "master.xlsx") -> dict:
    response = _upload_pump_xlsx(rows, filename)
    assert response.status_code == 200
    return response.json()["data"]


def _approve(session_id: str):
    return client.post("/api/ltsa/import/execute", json={"session_id": session_id})


class _RollbackInjectingRunner:
    """Delegates reads to a real DatabaseRunner (so the dry-run's own
    live-snapshot query still works) but always fails the write --
    reproduces a real transaction failure without touching execute_import/
    DatabaseRunner themselves (both reused unmodified)."""

    def __init__(self, real_runner):
        self._real = real_runner

    def query_scalar(self, sql: str) -> str:
        return self._real.query_scalar(sql)

    def execute_script(self, sql: str) -> None:
        raise RuntimeError("INJECTED FAILURE -- simulated transaction failure for MWO-LTSA-DATA-IMPORT-UI-001C")


def test_dry_run_persists_a_session_reachable_by_status_endpoint(real_db_cleanup):
    data = _dry_run_data((("PUMP-1", "TEST-ROUTER-P-SESS", "Unit 1", "OH", "11/61", None),))

    status_response = client.get(f"/api/ltsa/import/status/{data['session_id']}")
    body = status_response.json()

    assert body["success"] is True
    assert body["data"]["session_id"] == data["session_id"]
    assert body["data"]["status"] == "REVIEWING"


def test_a_rejected_file_cannot_approve_and_writes_nothing(real_db_cleanup):
    runner = _real_runner()
    # Real acceptance-file shape: a real tag_number, but missing 'area' --
    # same MISSING_REQUIRED_FIELD rejection the real RU II workbook's 5
    # rows hit. approval_ready must be false, and Approve must refuse to
    # write ANY of this package's rows (all-or-nothing), never a partial
    # 1-of-2 import.
    data = _dry_run_data(
        (
            ("PUMP-1", "TEST-ROUTER-P-REJ-1", "Unit 1", "OH", "11/61", None),
            ("PUMP-2", "TEST-ROUTER-P-REJ-2", None, "OH", "11/61", None),
        )
    )
    assert data["approval_ready"] is False
    assert data["rejected_count"] == 1

    response = _approve(data["session_id"])
    body = response.json()

    # Outer envelope success=true means the API call itself completed --
    # the real outcome (refused, all-or-nothing) is in data.status, the
    # same convention this router already uses for every execute result.
    assert body["success"] is True
    assert body["data"]["status"] == "REJECTED_INVALID"
    assert not _pump_present(runner, "TEST-ROUTER-P-REJ-1")
    assert not _pump_present(runner, "TEST-ROUTER-P-REJ-2")


def test_a_valid_file_can_approve_and_writes_exactly_the_reviewed_rows(real_db_cleanup):
    runner = _real_runner()
    data = _dry_run_data(
        (
            ("PUMP-1", "TEST-ROUTER-P-OK-1", "Unit 1", "OH", "11/61", None),
            ("PUMP-2", "TEST-ROUTER-P-OK-2", "Unit 2", "BB", "32/62", None),
        )
    )
    assert data["approval_ready"] is True
    assert not _pump_present(runner, "TEST-ROUTER-P-OK-1")  # zero writes before Approve

    response = _approve(data["session_id"])
    body = response.json()

    assert body["success"] is True
    assert body["data"]["status"] == "COMMITTED"
    assert body["data"]["session_id"] == data["session_id"]
    assert body["data"]["statistics"]["pump"]["inserted"] == 2
    assert _pump_present(runner, "TEST-ROUTER-P-OK-1")  # writes only after Approve
    assert _pump_present(runner, "TEST-ROUTER-P-OK-2")


def test_second_approve_is_blocked_and_does_not_execute_again(real_db_cleanup):
    runner = _real_runner()
    data = _dry_run_data((("PUMP-1", "TEST-ROUTER-P-REPLAY", "Unit 1", "OH", "11/61", None),))

    first = _approve(data["session_id"])
    assert first.json()["success"] is True
    assert first.json()["data"]["status"] == "COMMITTED"

    second = _approve(data["session_id"])
    second_body = second.json()

    assert second_body["success"] is False
    assert "already been executed" in second_body["message"]
    assert second_body["data"]["status"] == "IMPORTED"
    # Still exactly one row -- a second real INSERT never ran.
    rows = _json_query("SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number = 'TEST-ROUTER-P-REPLAY'", runner)
    assert rows == [{"n": 1}]


def test_approving_an_unknown_session_id_is_a_safe_error_not_a_crash():
    response = _approve("SESSION-DOES-NOT-EXIST")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is False
    assert "not found" in body["message"]


def test_transaction_rolls_back_on_an_injected_failure_and_marks_the_session_failed(real_db_cleanup):
    runner = _real_runner()
    data = _dry_run_data((("PUMP-1", "TEST-ROUTER-P-ROLLBACK", "Unit 1", "OH", "11/61", None),))

    failing_runner = _RollbackInjectingRunner(runner)
    app.dependency_overrides[get_import_database_runner] = lambda: failing_runner
    try:
        response = _approve(data["session_id"])
    finally:
        del app.dependency_overrides[get_import_database_runner]

    body = response.json()
    assert body["success"] is True  # the request itself succeeded -- it honestly reports a failed execution
    assert body["data"]["status"] == "FAILED_ROLLED_BACK"
    assert not _pump_present(runner, "TEST-ROUTER-P-ROLLBACK")

    status_response = client.get(f"/api/ltsa/import/status/{data['session_id']}")
    assert status_response.json()["data"]["status"] == "FAILED"


def test_approve_after_a_rolled_back_failure_is_also_blocked_as_already_executed(real_db_cleanup):
    # FAILED is terminal too (import_session.py's own IMPORT_SESSION_STATUSES)
    # -- a session that already failed once is not silently retried on a
    # second Approve click; a fresh dry-run is required.
    runner = _real_runner()
    data = _dry_run_data((("PUMP-1", "TEST-ROUTER-P-FAILRETRY", "Unit 1", "OH", "11/61", None),))

    failing_runner = _RollbackInjectingRunner(runner)
    app.dependency_overrides[get_import_database_runner] = lambda: failing_runner
    try:
        _approve(data["session_id"])
    finally:
        del app.dependency_overrides[get_import_database_runner]

    retry = _approve(data["session_id"])
    retry_body = retry.json()
    assert retry_body["success"] is False
    assert "already been executed" in retry_body["message"]


def test_approved_import_preserves_ab_and_arbr_as_distinct_rows(real_db_cleanup):
    runner = _real_runner()
    data = _dry_run_data(
        (
            ("PUMP-1", "TEST-ROUTER-P-13A", "Unit 1", "BB", "32/62", None),
            ("PUMP-2", "TEST-ROUTER-P-13AR", "Unit 1", "BB", "32/62", None),
            ("PUMP-3", "TEST-ROUTER-P-13B", "Unit 1", "BB", "32/62", None),
            ("PUMP-4", "TEST-ROUTER-P-13BR", "Unit 1", "BB", "32/62", None),
        )
    )
    assert data["approval_ready"] is True

    response = _approve(data["session_id"])
    assert response.json()["data"]["statistics"]["pump"]["inserted"] == 4

    for tag in ("TEST-ROUTER-P-13A", "TEST-ROUTER-P-13AR", "TEST-ROUTER-P-13B", "TEST-ROUTER-P-13BR"):
        assert _pump_present(runner, tag)


def test_approved_import_shows_insert_update_and_skip_in_the_execution_result(real_db_cleanup):
    runner = _real_runner()
    runner.execute_script("INSERT INTO ltsa_pumps (tag_number, area) VALUES ('TEST-ROUTER-P-APR-UPD', 'Unit 1');")
    data = _dry_run_data(
        (
            ("PUMP-1", "TEST-ROUTER-P-APR-NEW", "Unit 1", "OH", "11/61", None),
            ("PUMP-2", "TEST-ROUTER-P-APR-UPD", "Unit 1", "OH", "11/61", None),
        )
    )
    assert data["new_count"] == 1
    assert data["update_count"] == 1

    response = _approve(data["session_id"])
    stats = response.json()["data"]["statistics"]["pump"]

    assert stats["inserted"] == 1
    assert stats["updated"] == 1
    assert _pump_present(runner, "TEST-ROUTER-P-APR-NEW")
    live = _json_query("SELECT pump_type FROM ltsa_pumps WHERE tag_number = 'TEST-ROUTER-P-APR-UPD'", runner)
    assert live == [{"pump_type": "OH"}]
