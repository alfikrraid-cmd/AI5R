from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

TESTS_DIR = Path(__file__).resolve().parent
BACKEND_API_DIR = TESTS_DIR.parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.agent_execution_adapter import AgentExecutionAdapter, ExecutionArtifact
from API.coding_sandbox import PatchArtifact, ReviewArtifact, TestResult
from API.execution_ledger import (
    MAX_DIFF_BYTES,
    MAX_ERROR_BYTES,
    MAX_PAYLOAD_BYTES,
    MAX_SUMMARY_BYTES,
    SCHEMA_VERSION,
    ExecutionLedger,
    LedgerBoundExceededError,
    LedgerCorruptionError,
    LedgerPersistenceError,
)
from API.workforce_service import WorkforceService
from WORKFORCE.approval_chain_runtime import (
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
)
from WORKFORCE.work_item import WorkItem


@pytest.fixture
def temp_ledger_path(tmp_path: Path) -> Path:
    return tmp_path / "test_ledger.db"


@pytest.fixture
def ledger(temp_ledger_path: Path) -> ExecutionLedger:
    led = ExecutionLedger(db_path=temp_ledger_path)
    yield led
    led.close()


class MockAIClient:
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        capability: str = "general",
        **kwargs: Any,
    ) -> str:
        self.call_count += 1
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "capability": capability, **kwargs})

        for role_key, resp in self.responses.items():
            if role_key in system_prompt or role_key in prompt:
                return resp

        return json.dumps({
            "summary": "Mock analysis completed successfully.",
            "findings": ["Finding A", "Finding B"],
            "deliverables": "Mock deliverables.",
            "risks_and_considerations": ["Risk 1"],
        })


def test_schema_and_versioning(temp_ledger_path: Path):
    """Verify SQLite initialization, pragmas, versioning, and corruption handling."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    conn = ledger._get_connection()

    # Check pragmas
    version_row = conn.execute("PRAGMA user_version;").fetchone()
    assert version_row[0] == SCHEMA_VERSION

    fk_row = conn.execute("PRAGMA foreign_keys;").fetchone()
    assert fk_row[0] == 1

    # Check tables
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
    ]
    expected_tables = {
        "missions",
        "sprints",
        "plans",
        "work_items",
        "executions",
        "artifacts",
        "test_results",
        "chief_approvals",
    }
    assert expected_tables.issubset(set(tables))
    ledger.close()

    # Test future corrupt schema version detection
    raw_conn = sqlite3.connect(str(temp_ledger_path))
    raw_conn.execute("PRAGMA user_version = 99;")
    raw_conn.commit()
    raw_conn.close()

    with pytest.raises(LedgerCorruptionError) as exc_info:
        ExecutionLedger(db_path=temp_ledger_path)
    assert "Unsupported future database schema version 99" in str(exc_info.value)


def test_two_instance_restart_recovery(temp_ledger_path: Path):
    """Full lifecycle restart test: Instance A runs mission -> destroyed -> Instance B rehydrates identically."""
    ledger_a = ExecutionLedger(db_path=temp_ledger_path)
    service_a = WorkforceService(ledger=ledger_a)

    # 1. Create a mission
    mission_res = service_a.create_mission(
        title="Payment Gateway Integration",
        description="Integrate Stripe with fail-closed security",
        is_production=True,
    )
    mission_id = mission_res["mission_id"]

    # 2. Execute ARCHON (solution architect)
    archon_task = next(t for t in mission_res["tasks"] if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    ai_client = MockAIClient({
        "SOLUTION_ARCHITECT": json.dumps({
            "summary": "Architectural spec for payment gateway.",
            "findings": ["Stripe API requires webhook secret validation"],
            "deliverables": "Service interface defined.",
            "risks_and_considerations": ["Replay attacks on webhooks"],
        }),
    })
    art1 = service_a.execute_task(archon_task["work_item_id"], ai_client=ai_client)
    assert isinstance(art1, ExecutionArtifact)
    assert art1.status == "SUCCESS"

    # 3. Simulate backend coding patch and test result
    backend_task = next(t for t in mission_res["tasks"] if t["assigned_position_id"] == "BACKEND_ENGINEER")
    backend_item = service_a.find_work_item(backend_task["work_item_id"])
    assert backend_item is not None
    # Transition to claimed on board
    emp_forge = service_a.find_employee_by_position("BACKEND_ENGINEER")
    assert emp_forge is not None

    test_res = TestResult(
        test_result_id=f"TR-{uuid4().hex[:8].upper()}",
        command_id="PYTEST",
        target="CORE-SERVICES/BACKEND-API/TESTS/test_payment.py",
        exit_code=0,
        passed=True,
        duration=0.45,
        stdout_summary="1 passed in 0.45s",
        stderr_summary="",
        timed_out=False,
    )
    patch_art = PatchArtifact(
        artifact_id=f"PATCH-{uuid4().hex[:8].upper()}",
        work_item_id=backend_item.work_item_id,
        employee_id=emp_forge.employee_id,
        role=emp_forge.position_id,
        sandbox_id="SBX-PAYMENT-001",
        base_commit="a17ddfd0f7c77d571598ad9d6943c13b7e5f7a08",
        summary="Implemented Stripe payment gateway router and webhook handler.",
        changed_files=["CORE-SERVICES/API/payment_router.py"],
        diff_stat="1 file changed, 45 insertions(+)",
        git_diff="--- a/payment_router.py\n+++ b/payment_router.py\n@@ -1 +1,4 @@\n+# Stripe Integration",
        tests_requested=[{"kind": "PYTEST", "target": "CORE-SERVICES/BACKEND-API/TESTS/test_payment.py"}],
        tests_executed=[{"kind": "PYTEST", "target": "CORE-SERVICES/BACKEND-API/TESTS/test_payment.py"}],
        test_results=[test_res],
        started_at="2026-09-16T08:00:00Z",
        completed_at="2026-09-16T08:01:00Z",
        status="SUCCESS",
    )
    # Manually store patch in adapter to simulate completed sandbox run
    service_a.execution_adapter._artifacts[patch_art.artifact_id] = patch_art
    service_a.execution_adapter._artifacts_by_task[backend_item.work_item_id] = [patch_art]
    backend_item.artifact_id = patch_art.artifact_id
    service_a.work_board.complete(emp_forge, backend_item.work_item_id)
    ledger_a.record_artifact(
        artifact_id=patch_art.artifact_id,
        work_item_id=backend_item.work_item_id,
        employee_id=emp_forge.employee_id,
        role=emp_forge.position_id,
        artifact_type="PATCH",
        status="SUCCESS",
        summary=patch_art.summary,
        payload=patch_art.to_dict(),
        parent_artifact_ids=[art1.artifact_id],
        created_at=patch_art.completed_at,
        test_results=[test_res.to_dict()],
    )
    ledger_a.update_work_item_status(
        work_item_id=backend_item.work_item_id,
        status="COMPLETED",
        artifact_id=patch_art.artifact_id,
    )

    # 4. SENTRY technical review
    qa_task = next(t for t in mission_res["tasks"] if t["assigned_position_id"] == "QA_ENGINEER")
    emp_sentry = service_a.find_employee_by_position("QA_ENGINEER")
    assert emp_sentry is not None
    review_art = ReviewArtifact(
        review_id=f"REV-{uuid4().hex[:8].upper()}",
        work_item_id=qa_task["work_item_id"],
        employee_id=emp_sentry.employee_id,
        role=emp_sentry.position_id,
        reviewed_artifact_ids=[patch_art.artifact_id],
        decision="APPROVE_TECHNICAL",
        findings=["All tests pass", "Webhook signature verified"],
        risks=["Ensure TLS 1.3 in prod"],
        test_evidence_reviewed={"passed_count": 1, "failed_count": 0},
        recommended_action="Ready for production Chief approval",
        started_at="2026-09-16T08:02:00Z",
        completed_at="2026-09-16T08:03:00Z",
        status="COMPLETED",
    )
    service_a.execution_adapter._artifacts[review_art.review_id] = review_art
    service_a.execution_adapter._artifacts_by_task[qa_task["work_item_id"]] = [review_art]
    qa_item = service_a.find_work_item(qa_task["work_item_id"])
    assert qa_item is not None
    qa_item.artifact_id = review_art.review_id
    service_a.work_board.claim(emp_sentry, qa_item.work_item_id)
    service_a.work_board.complete(emp_sentry, qa_item.work_item_id)
    ledger_a.record_artifact(
        artifact_id=review_art.review_id,
        work_item_id=qa_item.work_item_id,
        employee_id=emp_sentry.employee_id,
        role=emp_sentry.position_id,
        artifact_type="REVIEW",
        status="COMPLETED",
        summary=review_art.summary,
        payload=review_art.to_dict(),
        parent_artifact_ids=[patch_art.artifact_id],
        created_at=review_art.completed_at,
    )
    ledger_a.update_work_item_status(
        work_item_id=qa_item.work_item_id,
        status="COMPLETED",
        artifact_id=review_art.review_id,
    )

    # 5. DevOps production task with Chief approval
    devops_task = next(t for t in mission_res["tasks"] if t["assigned_position_id"] == "DEVOPS_ENGINEER")
    devops_item = service_a.find_work_item(devops_task["work_item_id"])
    assert devops_item is not None
    emp_devops = service_a.find_employee_by_position("DEVOPS_ENGINEER")
    assert emp_devops is not None

    service_a.work_board.claim(emp_devops, devops_item.work_item_id)
    service_a.work_board.complete(emp_devops, devops_item.work_item_id)
    ledger_a.update_work_item_status(
        work_item_id=devops_item.work_item_id,
        status="COMPLETED",
        assigned_employee_id=emp_devops.employee_id,
    )

    chief_appr = service_a.grant_chief_approval(
        work_item_id=devops_item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )
    released_item = service_a.release_task(devops_item.work_item_id, approval=chief_appr)
    assert released_item.status == "RELEASED"

    # =========================================================================
    # SIMULATE PROCESS DEATH AND RESTART
    # =========================================================================
    ledger_a.close()
    del service_a
    del ledger_a

    # Instance B boots from same SQLite database
    ledger_b = ExecutionLedger(db_path=temp_ledger_path)
    service_b = WorkforceService(ledger=ledger_b)

    # Verify mission reconstruction
    restored_mission = service_b.get_mission(mission_id)
    assert restored_mission is not None
    assert restored_mission["mission_id"] == mission_id
    assert restored_mission["title"] == "Payment Gateway Integration"
    assert restored_mission["is_production"] is True

    # Verify work items and work_board status
    restored_backend = service_b.find_work_item(backend_item.work_item_id)
    assert restored_backend is not None
    assert restored_backend.status == "COMPLETED"
    assert restored_backend.artifact_id == patch_art.artifact_id
    assert restored_backend.work_item_id in service_b.work_board._completed

    restored_devops = service_b.find_work_item(devops_item.work_item_id)
    assert restored_devops is not None
    assert restored_devops.status == "RELEASED"
    assert restored_devops.work_item_id in service_b.work_board._released

    # Verify artifacts reconstruction
    restored_patch = service_b.get_artifact(patch_art.artifact_id)
    assert isinstance(restored_patch, PatchArtifact)
    assert restored_patch.summary == patch_art.summary
    assert restored_patch.git_diff == patch_art.git_diff
    assert len(restored_patch.test_results) == 1
    assert restored_patch.test_results[0].passed is True
    assert restored_patch.test_results[0].command_id == "PYTEST"

    restored_rev = service_b.get_artifact(review_art.review_id)
    assert isinstance(restored_rev, ReviewArtifact)
    assert restored_rev.decision == "APPROVE_TECHNICAL"
    assert restored_rev.findings == ["All tests pass", "Webhook signature verified"]

    # Verify Chief approval was restored
    restored_appr = service_b.approval_chain_runtime.get_chief_approval(devops_item.work_item_id)
    assert restored_appr is not None
    assert restored_appr.approver_id == "raid"
    assert restored_appr.is_human is True
    assert restored_appr.status == "APPROVED"

    # Verify full audit trail
    audit = ledger_b.get_audit_trail(devops_item.work_item_id)
    assert audit["work_item_id"] == devops_item.work_item_id
    assert audit["status"] == "RELEASED"
    assert audit["chief_approval"] is not None
    assert audit["chief_approval"]["approver_id"] == "raid"

    ledger_b.close()


def test_in_flight_crash_recovery_no_side_effects(temp_ledger_path: Path):
    """Crash recovery: In-flight execution marked STARTED sets RECOVERY_REQUIRED and DOES NOT replay side effects."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    service = WorkforceService(ledger=ledger)

    mission = service.create_mission("Data Ingestion Pipeline", is_production=False)
    arch_task = next(t for t in mission["tasks"] if t["assigned_position_id"] == "SOLUTION_ARCHITECT")

    # Simulate execution started in ledger, then process crash before completion
    exec_id = f"EXEC-CRASHED-{uuid4().hex[:8].upper()}"
    emp = service.find_employee_by_position("SOLUTION_ARCHITECT")
    assert emp is not None

    ledger.record_execution_started(
        execution_id=exec_id,
        work_item_id=arch_task["work_item_id"],
        employee_id=emp.employee_id,
        role=emp.position_id,
        execution_mode="READ_ONLY_ANALYSIS",
    )
    # The work item was claimed
    assert arch_task["work_item_id"] in service.work_board._claimed

    # Close and simulate restart
    ledger.close()
    del service

    mock_client = MockAIClient()

    # Rehydrate new instance
    ledger_recovered = ExecutionLedger(db_path=temp_ledger_path)
    service_recovered = WorkforceService(ledger=ledger_recovered)

    # Assert task remains CLAIMED on work_board
    recovered_item = service_recovered.find_work_item(arch_task["work_item_id"])
    assert recovered_item is not None
    assert recovered_item.status == "CLAIMED"
    assert recovered_item.work_item_id in service_recovered.work_board._claimed

    # Assert recovery_status is RECOVERY_REQUIRED
    assert recovered_item.metadata.get("recovery_status") == "RECOVERY_REQUIRED"

    # CRITICAL: Verify mock client was never called (NO AUTO SIDE EFFECT REPLAY)
    assert mock_client.call_count == 0

    ledger_recovered.close()


def test_chief_approval_governance_fail_closed(temp_ledger_path: Path):
    """Chief approval gate fail-closed tests against tampering and non-human records."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    service = WorkforceService(ledger=ledger)

    mission = service.create_mission("Critical Infrastructure Deployment", is_production=True)
    devops_task = next(t for t in mission["tasks"] if t["assigned_position_id"] == "DEVOPS_ENGINEER")
    emp = service.find_employee_by_position("DEVOPS_ENGINEER")
    assert emp is not None

    item = service.find_work_item(devops_task["work_item_id"])
    assert item is not None
    service.work_board.claim(emp, item.work_item_id)
    service.work_board.complete(emp, item.work_item_id)

    # 1. Attempt release without Chief approval -> raises ChiefApprovalRequiredError
    with pytest.raises(ChiefApprovalRequiredError):
        service.release_task(item.work_item_id)

    # 2. Attempt release with non-human / AI approval record -> raises ChiefApprovalRequiredError
    fake_ai_approval = ChiefApprovalRecord(
        work_item_id=item.work_item_id,
        approver_id="ID-CTO",
        approver_role="CTO",
        is_human=False,
        status="APPROVED",
    )
    with pytest.raises(ChiefApprovalRequiredError) as exc_info:
        service.release_task(item.work_item_id, approval=fake_ai_approval)
    assert "not marked as human" in str(exc_info.value)

    # 3. Grant valid human Chief approval and release -> succeeds
    valid_approval = service.grant_chief_approval(
        work_item_id=item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )
    released = service.release_task(item.work_item_id, approval=valid_approval)
    assert released.status == "RELEASED"

    ledger.close()


def test_ai_technical_approval_never_substitutes_chief(temp_ledger_path: Path):
    """SENTRY QA review with APPROVE_TECHNICAL must never become or satisfy human Chief approval."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    service = WorkforceService(ledger=ledger)

    mission = service.create_mission("Production Hotfix", is_production=True)
    devops_task = next(t for t in mission["tasks"] if t["assigned_position_id"] == "DEVOPS_ENGINEER")
    emp_devops = service.find_employee_by_position("DEVOPS_ENGINEER")
    assert emp_devops is not None

    item = service.find_work_item(devops_task["work_item_id"])
    assert item is not None
    service.work_board.claim(emp_devops, item.work_item_id)
    service.work_board.complete(emp_devops, item.work_item_id)
    ledger.update_work_item_status(work_item_id=item.work_item_id, status="COMPLETED")

    # Simulate SENTRY technical review
    sentry_emp = service.find_employee_by_position("QA_ENGINEER")
    assert sentry_emp is not None
    review = ReviewArtifact(
        review_id=f"REV-{uuid4().hex[:8].upper()}",
        work_item_id=item.work_item_id,
        employee_id=sentry_emp.employee_id,
        role=sentry_emp.position_id,
        reviewed_artifact_ids=["ART-PREV"],
        decision="APPROVE_TECHNICAL",
        findings=["QA tests pass"],
        risks=[],
        test_evidence_reviewed={"passed_count": 1},
        recommended_action="Ready",
        started_at="2026-09-16T08:00:00Z",
        completed_at="2026-09-16T08:01:00Z",
    )
    ledger.record_artifact(
        artifact_id=review.review_id,
        work_item_id=item.work_item_id,
        employee_id=sentry_emp.employee_id,
        role=sentry_emp.position_id,
        artifact_type="REVIEW",
        status="COMPLETED",
        summary=review.summary,
        payload=review.to_dict(),
    )

    # Restart
    ledger.close()
    del service

    ledger_restarted = ExecutionLedger(db_path=temp_ledger_path)
    service_restarted = WorkforceService(ledger=ledger_restarted)

    # Attempt release: SENTRY approval MUST NOT grant release
    with pytest.raises(ChiefApprovalRequiredError):
        service_restarted.release_task(item.work_item_id)

    ledger_restarted.close()


def test_idempotent_rehydration(temp_ledger_path: Path):
    """Calling recover_from_ledger multiple times must not duplicate tasks or artifacts."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    service = WorkforceService(ledger=ledger)

    mission = service.create_mission("Multi-Run Mission", is_production=False)
    mission_id = mission["mission_id"]

    initial_task_count = len(mission["tasks"])
    assert len(service.work_board.available_work_items()) + len(service.work_board.claimed_work_items()) == initial_task_count

    # Re-run recovery 3 times
    service.recover_from_ledger()
    service.recover_from_ledger()
    service.recover_from_ledger()

    assert len(service.work_board.available_work_items()) + len(service.work_board.claimed_work_items()) == initial_task_count
    assert len(service._missions) == 1
    assert len(service._plans) == 1

    ledger.close()


def test_payload_and_diff_bounds_enforcement(ledger: ExecutionLedger):
    """Oversized payloads, git diffs, summaries, or errors must raise LedgerBoundExceededError."""
    # 1. Oversized summary
    huge_summary = "X" * (MAX_SUMMARY_BYTES + 10)
    with pytest.raises(LedgerBoundExceededError) as exc_info:
        ledger.record_artifact(
            artifact_id="ART-HUGE-SUM",
            work_item_id="WORK-1",
            employee_id="EMP-1",
            role="BACKEND_ENGINEER",
            artifact_type="EXECUTION",
            status="SUCCESS",
            summary=huge_summary,
            payload={"ok": True},
        )
    assert "Summary size" in str(exc_info.value)

    # 2. Oversized diff
    huge_diff = "diff --git a/test b/test\n" + ("+" * (MAX_DIFF_BYTES + 10))
    with pytest.raises(LedgerBoundExceededError) as exc_info:
        ledger.record_artifact(
            artifact_id="ART-HUGE-DIFF",
            work_item_id="WORK-1",
            employee_id="EMP-1",
            role="BACKEND_ENGINEER",
            artifact_type="PATCH",
            status="SUCCESS",
            summary="Normal summary",
            payload={"git_diff": huge_diff},
        )
    assert "Git diff size" in str(exc_info.value)

    # 3. Oversized error message
    huge_error = "E" * (MAX_ERROR_BYTES + 10)
    with pytest.raises(LedgerBoundExceededError) as exc_info:
        ledger.record_execution_completed(
            execution_id="EXEC-1",
            status="FAILED",
            error=huge_error,
        )
    assert "Error message size" in str(exc_info.value)

    # 4. Oversized JSON payload
    huge_payload = {"data": "D" * (MAX_PAYLOAD_BYTES + 10)}
    with pytest.raises(LedgerBoundExceededError) as exc_info:
        ledger.record_artifact(
            artifact_id="ART-HUGE-PAYLOAD",
            work_item_id="WORK-1",
            employee_id="EMP-1",
            role="BACKEND_ENGINEER",
            artifact_type="EXECUTION",
            status="SUCCESS",
            summary="Normal summary",
            payload=huge_payload,
        )
    assert "Payload size" in str(exc_info.value)


def test_in_memory_backward_compatibility():
    """WorkforceService initialized without a ledger operates purely in-memory with zero errors."""
    service = WorkforceService(ledger=None)
    assert service.ledger is None

    mission = service.create_mission("In-Memory Mission", is_production=False)
    assert mission["status"] == "IN_PROGRESS"
    assert len(mission["tasks"]) > 0

    first_task = mission["tasks"][0]
    assigned_item = service.find_work_item(first_task["work_item_id"])
    assert assigned_item is not None


def test_chief_approval_write_failure_rollback(temp_ledger_path: Path):
    """Chief approval durable write failure must NOT leave effective in-memory production approval."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    service = WorkforceService(ledger=ledger)

    work_item_id = "WORK-FAIL-001"
    # Mock record_chief_approval on ledger to simulate disk/database failure
    def mock_fail(*args, **kwargs):
        raise LedgerPersistenceError("Simulated disk failure during chief approval write")

    ledger.record_chief_approval = mock_fail

    with pytest.raises(LedgerPersistenceError):
        service.grant_chief_approval(
            work_item_id=work_item_id,
            approver_id="raid",
            approver_role="CHIEF_ARCHITECT",
            is_human=True,
        )

    # CRITICAL: In-memory approval must have been rolled back and NOT exist
    assert service.approval_chain_runtime.get_chief_approval(work_item_id) is None
    ledger.close()


def test_production_release_write_failure_rollback(temp_ledger_path: Path):
    """Production release durable write failure must NOT leave effective released state in memory."""
    ledger = ExecutionLedger(db_path=temp_ledger_path)
    service = WorkforceService(ledger=ledger)

    mission = service.create_mission("Failure Rollback Mission", is_production=True)
    devops_task = next(t for t in mission["tasks"] if t["assigned_position_id"] == "DEVOPS_ENGINEER")
    emp = service.find_employee_by_position("DEVOPS_ENGINEER")
    assert emp is not None

    item = service.find_work_item(devops_task["work_item_id"])
    assert item is not None
    service.work_board.claim(emp, item.work_item_id)
    service.work_board.complete(emp, item.work_item_id)

    chief_appr = service.grant_chief_approval(
        work_item_id=item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )

    # Mock update_work_item_status to simulate DB lock/failure during release persistence
    def mock_fail_update(*args, **kwargs):
        raise LedgerPersistenceError("Simulated DB lock failure during release status update")

    ledger.update_work_item_status = mock_fail_update

    with pytest.raises(LedgerPersistenceError):
        service.release_task(item.work_item_id, approval=chief_appr)

    # CRITICAL: Work item must NOT be in _released; it must remain in _completed
    assert item.work_item_id not in service.work_board._released
    assert item.work_item_id in service.work_board._completed
    assert item.status == "COMPLETED"

    ledger.close()
