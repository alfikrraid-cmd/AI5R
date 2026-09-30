import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
import pytest

BACKEND_API_DIR = Path(__file__).resolve().parent.parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"

for p in (str(BACKEND_API_DIR), str(CORE_SERVICES_DIR), str(AI5R_SDK_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from API.coding_sandbox import (
    CodingSandbox,
    MAX_AUTOMATIC_REVISIONS,
    PatchArtifact,
    PathSecurityError,
    ReviewArtifact,
    RevisionAttempt,
    SandboxManager,
    TestResult,
)
from API.agent_execution_adapter import AgentExecutionAdapter
from API.execution_ledger import ExecutionLedger, LedgerPersistenceError
from API.workforce_service import WorkforceService
from WORKFORCE.approval_chain_runtime import (
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
)
from WORKFORCE.work_item import WorkItem


class SequenceMockAI:
    """Deterministic AI client double returning sequential structured JSON responses."""

    def __init__(self, responses: list[dict[str, Any] | str]) -> None:
        self.responses = responses
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
        else:
            resp = self.responses[-1]
        self.call_count += 1
        if isinstance(resp, str):
            return resp
        return json.dumps(resp)


@pytest.fixture
def temp_ledger_db(tmp_path: Path) -> Path:
    return tmp_path / "test_revision_ledger.db"


@pytest.fixture
def sandbox_manager() -> SandboxManager:
    return SandboxManager(repo_dir=REPO_ROOT)


# ==============================================================================
# 1. SUCCESS PATH — 1 REVISION
# ==============================================================================
def test_1_success_path_one_revision(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """Initial patch with test failure -> SENTRY REQUEST_CHANGES -> Revision 1 fixes test -> SENTRY APPROVE_TECHNICAL -> STOP."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Revision Org", ledger=ledger)
    service.execution_adapter.sandbox_manager = sandbox_manager

    assign_res = service.assign_task(
        title="Implement Auth Token Validator",
        position_id="BACKEND_ENGINEER",
        is_production=True,
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Initial coding: introduces bug in test
    initial_ai = SequenceMockAI([
        {
            "summary": "Initial token validator with buggy test",
            "changes": [
                {
                    "path": "CORE-SERVICES/auth_tok.py",
                    "operation": "create",
                    "content": "def validate_token(t):\n    return t == 'valid-secret'\n",
                },
                {
                    "path": "CORE-SERVICES/test_auth_tok.py",
                    "operation": "create",
                    "content": "from auth_tok import validate_token\ndef test_tok():\n    assert validate_token('wrong') is True\n",  # fails!
                },
            ],
            "requested_tests": [
                {"kind": "PYTEST", "target": "CORE-SERVICES/test_auth_tok.py"}
            ],
        }
    ])

    patch_0 = service.execute_task(work_item_id, ai_client=initial_ai)
    assert isinstance(patch_0, PatchArtifact)
    assert len(patch_0.test_results) == 1
    assert patch_0.test_results[0].passed is False

    # SENTRY initial review: evaluates patch_0 and must REQUEST_CHANGES due to truthfulness guard
    sentry_mock_1 = SequenceMockAI([
        {
            "decision": "APPROVE_TECHNICAL",  # Model claims approve, but truthfulness guard will override to REQUEST_CHANGES
            "summary": "Reviewed code",
            "findings": ["Test failed"],
            "risks": ["Auth bypass"],
            "recommended_action": "Fix test assertion",
        }
    ])
    review_0 = service.execution_adapter._perform_sentry_review(
        work_item=service.find_work_item(work_item_id),
        sentry_employee=service.find_employee_by_position("QA_ENGINEER"),
        patch_artifact=patch_0,
        ai_client=sentry_mock_1,
        attempt_number=0,
    )
    assert review_0.decision == "REQUEST_CHANGES"

    # Now verify eligibility
    eligible, reason = service.check_revision_eligibility(work_item_id)
    assert eligible is True

    # Revision 1 AI: fixes the test
    revision_ai = SequenceMockAI([
        {
            "summary": "Fixed test assertion to check valid token",
            "changes": [
                {
                    "path": "CORE-SERVICES/test_auth_tok.py",
                    "operation": "modify",
                    "content": "from auth_tok import validate_token\ndef test_tok():\n    assert validate_token('valid-secret') is True\n",
                }
            ],
            "requested_tests": [
                {"kind": "PYTEST", "target": "CORE-SERVICES/test_auth_tok.py"}
            ],
        }
    ])

    # SENTRY Revision 1 review: APPROVE_TECHNICAL
    sentry_approve_ai = SequenceMockAI([
        {
            "decision": "APPROVE_TECHNICAL",
            "summary": "All tests now pass cleanly. Approved.",
            "findings": [],
            "risks": [],
            "recommended_action": "Ready for Chief approval",
        }
    ])

    rev_res = service.execute_revision(
        work_item_id=work_item_id,
        ai_client=revision_ai,
        sentry_client=sentry_approve_ai,
    )

    assert rev_res["status"] == "APPROVED"
    assert rev_res["attempt_number"] == 1
    patch_1 = rev_res["patch"]
    review_1 = rev_res["review"]
    assert patch_1.artifact_id != patch_0.artifact_id
    assert patch_1.test_results[0].passed is True
    assert review_1.decision == "APPROVE_TECHNICAL"

    # Verifications
    assert service.execution_adapter.get_revision_count(work_item_id) == 1
    # Revision 2 was NOT created
    assert len(service.execution_adapter.get_task_revisions(work_item_id)) == 1
    # Chief approval NOT automatically created
    assert work_item_id not in service.approval_chain_runtime._chief_approvals
    # Production NOT released
    work_item = service.find_work_item(work_item_id)
    assert work_item.status == "COMPLETED"


# ==============================================================================
# 2. TWO REVISION PATH
# ==============================================================================
def test_2_two_revision_path_success(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """Initial -> REQUEST_CHANGES -> Revision 1 -> REQUEST_CHANGES -> Revision 2 -> APPROVE_TECHNICAL -> STOP."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Revision Org 2", ledger=ledger)
    service.execution_adapter.sandbox_manager = sandbox_manager

    assign_res = service.assign_task(
        title="Implement Rate Limiter",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Initial coding (fails)
    initial_ai = SequenceMockAI([{
        "summary": "Initial rate limiter",
        "changes": [
            {"path": "CORE-SERVICES/rate_lim.py", "operation": "create", "content": "LIMIT = 10\n"},
            {"path": "CORE-SERVICES/test_rate_lim.py", "operation": "create", "content": "from rate_lim import LIMIT\ndef test_r(): assert LIMIT == 100\n"},
        ],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_rate_lim.py"}],
    }])
    patch_0 = service.execute_task(work_item_id, ai_client=initial_ai)

    # Review 0: REQUEST_CHANGES
    review_0_ai = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Tests failed",
        "findings": ["AssertionError on limit value"],
        "risks": [],
        "recommended_action": "Fix limit value",
    }])
    service.execution_adapter._perform_sentry_review(
        work_item=service.find_work_item(work_item_id),
        sentry_employee=service.find_employee_by_position("QA_ENGINEER"),
        patch_artifact=patch_0,
        ai_client=review_0_ai,
        attempt_number=0,
    )

    # Revision 1 AI: still buggy
    rev_1_ai = SequenceMockAI([{
        "summary": "Adjusted limit partially",
        "changes": [{"path": "CORE-SERVICES/rate_lim.py", "operation": "modify", "content": "LIMIT = 50\n"}],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_rate_lim.py"}],
    }])
    sentry_reject_ai = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Still failing",
        "findings": ["Limit is 50, expected 100"],
        "risks": [],
        "recommended_action": "Set to 100",
    }])

    rev_1_res = service.execute_revision(
        work_item_id=work_item_id,
        ai_client=rev_1_ai,
        sentry_client=sentry_reject_ai,
    )
    assert rev_1_res["status"] == "REQUEST_CHANGES"
    assert rev_1_res["attempt_number"] == 1

    # Revision 2 AI: fixes it completely
    rev_2_ai = SequenceMockAI([{
        "summary": "Set limit to 100",
        "changes": [{"path": "CORE-SERVICES/rate_lim.py", "operation": "modify", "content": "LIMIT = 100\n"}],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_rate_lim.py"}],
    }])
    sentry_approve_ai = SequenceMockAI([{
        "decision": "APPROVE_TECHNICAL",
        "summary": "All tests pass",
        "findings": [],
        "risks": [],
        "recommended_action": "Approved",
    }])

    rev_2_res = service.execute_revision(
        work_item_id=work_item_id,
        ai_client=rev_2_ai,
        sentry_client=sentry_approve_ai,
    )
    assert rev_2_res["status"] == "APPROVED"
    assert rev_2_res["attempt_number"] == 2

    # Verify bounds
    assert service.execution_adapter.get_revision_count(work_item_id) == 2
    # No revision 3 created
    eligible, reason = service.check_revision_eligibility(work_item_id)
    assert eligible is False


# ==============================================================================
# 3. EXHAUSTION PATH — STOP AT 2 AND ESCALATE
# ==============================================================================
def test_3_exhaustion_path_escalates_to_human_chief(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """Initial -> REQUEST_CHANGES -> Rev 1 -> REQUEST_CHANGES -> Rev 2 -> REQUEST_CHANGES -> ESCALATION_REQUIRED. No Rev 3."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Exhaustion Org", ledger=ledger)
    service.execution_adapter.sandbox_manager = sandbox_manager

    assign_res = service.assign_task(
        title="Implement Complex Cipher",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Initial coding (fails)
    initial_ai = SequenceMockAI([{
        "summary": "Initial cipher",
        "changes": [
            {"path": "CORE-SERVICES/cipher_c.py", "operation": "create", "content": "CIPHER = 'bad'\n"},
            {"path": "CORE-SERVICES/test_cipher_c.py", "operation": "create", "content": "from cipher_c import CIPHER\ndef test_c(): assert CIPHER == 'good'\n"},
        ],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_cipher_c.py"}],
    }])
    patch_0 = service.execute_task(work_item_id, ai_client=initial_ai)

    # Initial SENTRY review: REQUEST_CHANGES
    review_0_ai = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Initial cipher failed",
        "findings": ["Cipher mismatch"],
        "risks": [],
        "recommended_action": "Fix cipher",
    }])
    service.execution_adapter._perform_sentry_review(
        work_item=service.find_work_item(work_item_id),
        sentry_employee=service.find_employee_by_position("QA_ENGINEER"),
        patch_artifact=patch_0,
        ai_client=review_0_ai,
        attempt_number=0,
    )

    # Revision 1 AI: still failing
    rev_1_ai = SequenceMockAI([{
        "summary": "Attempt 1 fix",
        "changes": [{"path": "CORE-SERVICES/cipher_c.py", "operation": "modify", "content": "CIPHER = 'still_bad'\n"}],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_cipher_c.py"}],
    }])
    sentry_reject_1 = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Still mismatch",
        "findings": ["Cipher still bad"],
        "risks": [],
        "recommended_action": "Fix cipher",
    }])

    rev_1_res = service.execute_revision(
        work_item_id=work_item_id,
        ai_client=rev_1_ai,
        sentry_client=sentry_reject_1,
    )
    assert rev_1_res["status"] == "REQUEST_CHANGES"
    assert rev_1_res["attempt_number"] == 1

    # Revision 2 AI: still failing
    rev_2_ai = SequenceMockAI([{
        "summary": "Attempt 2 fix",
        "changes": [{"path": "CORE-SERVICES/cipher_c.py", "operation": "modify", "content": "CIPHER = 'almost_good'\n"}],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_cipher_c.py"}],
    }])
    sentry_reject_2 = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Revision 2 still fails",
        "findings": ["Cipher did not match expected value"],
        "risks": ["Data corruption"],
        "recommended_action": "Human review required",
    }])

    rev_2_res = service.execute_revision(
        work_item_id=work_item_id,
        ai_client=rev_2_ai,
        sentry_client=sentry_reject_2,
    )

    # Hard bound exhaustion assertion
    assert rev_2_res["status"] == "ESCALATION_REQUIRED"
    assert rev_2_res["attempt_number"] == 2

    work_item = service.find_work_item(work_item_id)
    assert work_item.metadata.get("recovery_status") == "ESCALATION_REQUIRED"
    assert work_item.metadata.get("escalation_reason") == "REVISION_LIMIT_EXHAUSTED"

    # Assert NO Revision 3 can be started
    eligible, reason = service.check_revision_eligibility(work_item_id)
    assert eligible is False
    assert "Revision limit reached" in reason

    with pytest.raises(ValueError, match="not eligible"):
        service.execute_revision(work_item_id)

    assert service.execution_adapter.get_revision_count(work_item_id) == 2


# ==============================================================================
# 4. RESTART DURING REVISION — ZERO SIDE EFFECT REPLAY
# ==============================================================================
def test_4_restart_during_revision_recovers_as_recovery_required(temp_ledger_db: Path):
    """Crash mid-revision -> Boot new instance B -> Recovers as RECOVERY_REQUIRED without replaying LLM or tests."""
    ledger_a = ExecutionLedger(temp_ledger_db)
    service_a = WorkforceService(organization_name="Restart Org", ledger=ledger_a)

    assign_res = service_a.assign_task(
        title="Payment Service Implementation",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Record revision attempt that simulates crash mid-flight (status EXECUTING)
    rev_id = "REV-ATTEMPT-1-CRASHED"
    ledger_a.record_revision_attempt(
        revision_id=rev_id,
        work_item_id=work_item_id,
        employee_id="EMP-FORGE",
        role="BACKEND_ENGINEER",
        attempt_number=1,
        status="EXECUTING",
        started_at="2026-09-17T00:00:00Z",
    )

    # Destroy instance A
    ledger_a.close()
    del service_a
    del ledger_a

    # Track any LLM invocation on instance B
    llm_called = False
    class SentinelAI:
        def generate(self, *args, **kwargs):
            nonlocal llm_called
            llm_called = True
            raise AssertionError("Side effect replayed during rehydration!")

    # Boot new instance B with zero object reuse
    ledger_b = ExecutionLedger(temp_ledger_db)
    service_b = WorkforceService(
        organization_name="Restart Org",
        ledger=ledger_b,
        auto_recover=True,
    )
    service_b.execution_adapter.ai_client = SentinelAI()

    # Assert ZERO side-effect replay
    assert llm_called is False

    # Assert recovered revision status
    revisions = ledger_b.load_revisions(work_item_id)
    assert len(revisions) == 1
    recovered_rev = revisions[0]
    assert recovered_rev["revision_id"] == rev_id
    assert recovered_rev["status"] == "RECOVERY_REQUIRED"

    # Assert work item state
    item_b = service_b.find_work_item(work_item_id)
    assert item_b is not None
    assert item_b.status == "CLAIMED"
    assert item_b.metadata.get("recovery_status") == "RECOVERY_REQUIRED"


# ==============================================================================
# 5. LINEAGE RECONSTRUCTION ACROSS RESTARTS
# ==============================================================================
def test_5_full_lineage_reconstruction_across_restart(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """Reconstruct complete lineage (WorkItem -> Patch0 -> Test0 -> Rev0 -> RevAttempt1 -> Patch1 -> Test1 -> Rev1) from DB alone."""
    ledger_a = ExecutionLedger(temp_ledger_db)
    service_a = WorkforceService(organization_name="Lineage Org", ledger=ledger_a)
    service_a.execution_adapter.sandbox_manager = sandbox_manager

    assign_res = service_a.assign_task(
        title="Audit Logging Service",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Initial coding
    initial_ai = SequenceMockAI([{
        "summary": "Audit log v1",
        "changes": [{"path": "CORE-SERVICES/audit.py", "operation": "create", "content": "AUDIT=1\n"}],
        "requested_tests": [],
    }])
    patch_0 = service_a.execute_task(work_item_id, ai_client=initial_ai)

    review_0_ai = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Requires automated test",
        "findings": ["No tests requested"],
        "risks": ["Unverified regression"],
        "recommended_action": "Add pytest",
    }])
    review_0 = service_a.execution_adapter._perform_sentry_review(
        work_item=service_a.find_work_item(work_item_id),
        sentry_employee=service_a.find_employee_by_position("QA_ENGINEER"),
        patch_artifact=patch_0,
        ai_client=review_0_ai,
        attempt_number=0,
    )

    # Revision 1
    rev_1_ai = SequenceMockAI([{
        "summary": "Added audit test",
        "changes": [
            {"path": "CORE-SERVICES/test_audit.py", "operation": "create", "content": "from audit import AUDIT\ndef test_a(): assert AUDIT == 1\n"}
        ],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_audit.py"}],
    }])
    sentry_approve_ai = SequenceMockAI([{
        "decision": "APPROVE_TECHNICAL",
        "summary": "Test verified and passing",
        "findings": [],
        "risks": [],
        "recommended_action": "Approved",
    }])

    rev_1_res = service_a.execute_revision(
        work_item_id=work_item_id,
        ai_client=rev_1_ai,
        sentry_client=sentry_approve_ai,
    )
    assert rev_1_res["status"] == "APPROVED"

    # Close instance A
    ledger_a.close()
    del service_a
    del ledger_a

    # Reconstruct in instance B
    ledger_b = ExecutionLedger(temp_ledger_db)
    service_b = WorkforceService(organization_name="Lineage Org", ledger=ledger_b, auto_recover=True)

    audit_trail = ledger_b.get_audit_trail(work_item_id)
    assert audit_trail["work_item_id"] == work_item_id
    assert len(audit_trail["revisions"]) == 1
    assert audit_trail["revisions"][0]["attempt_number"] == 1
    assert audit_trail["revisions"][0]["status"] == "COMPLETED"

    # Artifact lineage
    artifacts = audit_trail["artifacts"]
    assert len(artifacts) == 4  # Patch 0, Review 0, Patch 1, Review 1
    patch_arts = [a for a in artifacts if a["artifact_type"] == "PATCH"]
    review_arts = [a for a in artifacts if a["artifact_type"] == "REVIEW"]
    assert len(patch_arts) == 2
    assert len(review_arts) == 2

    # Verify parent artifact relationship survived restart
    r1_patch = patch_arts[1]
    assert patch_0.artifact_id in r1_patch["parent_artifact_ids"]
    assert review_0.review_id in r1_patch["parent_artifact_ids"]


# ==============================================================================
# 6. SECURITY & GOVERNANCE TESTS
# ==============================================================================
def test_6_security_non_coding_roles_denied_revision(temp_ledger_db: Path):
    """Roles other than BACKEND_ENGINEER and FRONTEND_ENGINEER cannot execute revisions."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Security Org", ledger=ledger)

    for non_coding_pos in ("SOLUTION_ARCHITECT", "DEVOPS_ENGINEER", "SECURITY_ENGINEER", "QA_ENGINEER"):
        assign_res = service.assign_task(
            title=f"Non coding task for {non_coding_pos}",
            position_id=non_coding_pos,
        )
        w_id = assign_res["work_item"]["work_item_id"]

        eligible, reason = service.check_revision_eligibility(w_id)
        assert eligible is False
        assert "not authorized for autonomous revision" in reason

        with pytest.raises(ValueError, match="not eligible"):
            service.execute_revision(w_id)


def test_7_security_client_cannot_override_max_revisions(temp_ledger_db: Path):
    """Hard backend limit MAX_AUTOMATIC_REVISIONS = 2 cannot be overridden."""
    assert MAX_AUTOMATIC_REVISIONS == 2
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Limit Org", ledger=ledger)

    assign_res = service.assign_task(
        title="Coding Task",
        position_id="BACKEND_ENGINEER",
    )
    w_id = assign_res["work_item"]["work_item_id"]

    # Record 2 existing revisions directly in ledger
    ledger.record_revision_attempt(
        revision_id="REV-1",
        work_item_id=w_id,
        employee_id="EMP-FORGE",
        role="BACKEND_ENGINEER",
        attempt_number=1,
        status="COMPLETED",
    )
    ledger.record_revision_attempt(
        revision_id="REV-2",
        work_item_id=w_id,
        employee_id="EMP-FORGE",
        role="BACKEND_ENGINEER",
        attempt_number=2,
        status="COMPLETED",
    )

    eligible, reason = service.check_revision_eligibility(w_id)
    assert eligible is False
    assert "Revision limit reached" in reason

    with pytest.raises(ValueError, match="not eligible"):
        service.execute_revision(w_id)


def test_8_security_duplicate_attempt_number_fails_closed(temp_ledger_db: Path):
    """Unique constraint on (work_item_id, attempt_number) prevents duplicate revision records."""
    ledger = ExecutionLedger(temp_ledger_db)

    # Record parent work item first to satisfy foreign key constraint
    ledger.record_work_item({
        "work_item_id": "WORK-DUP",
        "title": "Duplicate Test Work Item",
        "assigned_position_id": "BACKEND_ENGINEER",
        "status": "CREATED",
    })

    # First attempt succeeds
    ledger.record_revision_attempt(
        revision_id="REV-1A",
        work_item_id="WORK-DUP",
        employee_id="EMP-FORGE",
        role="BACKEND_ENGINEER",
        attempt_number=1,
        status="EXECUTING",
    )

    # Duplicate attempt number for same work item must raise LedgerPersistenceError
    with pytest.raises(LedgerPersistenceError, match="Duplicate or invalid revision attempt"):
        ledger.record_revision_attempt(
            revision_id="REV-1B",
            work_item_id="WORK-DUP",
            employee_id="EMP-FORGE",
            role="BACKEND_ENGINEER",
            attempt_number=1,
            status="EXECUTING",
        )


def test_9_security_sentry_approve_never_releases_production(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """SENTRY APPROVE_TECHNICAL on revision does NOT create Chief approval or release production task."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Chief Gate Org", ledger=ledger)
    service.execution_adapter.sandbox_manager = sandbox_manager

    assign_res = service.assign_task(
        title="Production Data Mutation Module",
        position_id="BACKEND_ENGINEER",
        is_production=True,
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Initial coding
    initial_ai = SequenceMockAI([{
        "summary": "Prod module",
        "changes": [
            {"path": "CORE-SERVICES/prod_mod.py", "operation": "create", "content": "P=1\n"},
            {"path": "CORE-SERVICES/test_prod_mod.py", "operation": "create", "content": "from prod_mod import P\ndef test_p(): assert P == 0\n"},
        ],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_prod_mod.py"}],
    }])
    patch_0 = service.execute_task(work_item_id, ai_client=initial_ai)

    # SENTRY rejects initial
    review_0_ai = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Failed test",
        "findings": ["Test failed"],
        "risks": [],
        "recommended_action": "Fix",
    }])
    service.execution_adapter._perform_sentry_review(
        work_item=service.find_work_item(work_item_id),
        sentry_employee=service.find_employee_by_position("QA_ENGINEER"),
        patch_artifact=patch_0,
        ai_client=review_0_ai,
        attempt_number=0,
    )

    # Revision 1: passes
    rev_ai = SequenceMockAI([{
        "summary": "Fix prod test",
        "changes": [{"path": "CORE-SERVICES/test_prod_mod.py", "operation": "modify", "content": "from prod_mod import P\ndef test_p(): assert P == 1\n"}],
        "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_prod_mod.py"}],
    }])
    sentry_approve = SequenceMockAI([{
        "decision": "APPROVE_TECHNICAL",
        "summary": "Passed",
        "findings": [],
        "risks": [],
        "recommended_action": "Ready for Chief approval",
    }])

    rev_res = service.execute_revision(
        work_item_id=work_item_id,
        ai_client=rev_ai,
        sentry_client=sentry_approve,
    )
    assert rev_res["status"] == "APPROVED"

    # SENTRY approval MUST NOT release production task without Human Chief
    with pytest.raises(ChiefApprovalRequiredError, match="Human Chief approval is MISSING"):
        service.release_task(work_item_id)

    # Only explicit human Chief approval permits release
    chief_rec = ChiefApprovalRecord(
        work_item_id=work_item_id,
        approver_id="CHIEF-HUMAN",
        approver_role="CHIEF",
        is_human=True,
    )
    released = service.release_task(work_item_id, approval=chief_rec)
    assert released.status == "RELEASED"


def test_10_security_parallel_revision_blocked(temp_ledger_db: Path):
    """WorkItem currently in _revising_tasks cannot start concurrent revision."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Parallel Org", ledger=ledger)

    assign_res = service.assign_task(
        title="Parallel Guard Test",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Add to in-flight set
    service.execution_adapter._revising_tasks.add(work_item_id)

    eligible, reason = service.check_revision_eligibility(work_item_id)
    assert eligible is False
    assert "currently executing or revising" in reason

    with pytest.raises(ValueError, match="currently executing or revising"):
        service.execute_revision(work_item_id)


def test_11_security_path_traversal_in_revision_rejected(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """Specialist attempting traversal escape in revision is blocked and fails closed."""
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Traversal Org", ledger=ledger)
    service.execution_adapter.sandbox_manager = sandbox_manager

    assign_res = service.assign_task(
        title="Traversal Test",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    # Initial coding
    initial_ai = SequenceMockAI([{
        "summary": "Initial",
        "changes": [{"path": "CORE-SERVICES/t.py", "operation": "create", "content": "T=1\n"}],
        "requested_tests": [],
    }])
    patch_0 = service.execute_task(work_item_id, ai_client=initial_ai)

    review_0_ai = SequenceMockAI([{
        "decision": "REQUEST_CHANGES",
        "summary": "Fix needed",
        "findings": ["Need update"],
        "risks": [],
        "recommended_action": "Update",
    }])
    service.execution_adapter._perform_sentry_review(
        work_item=service.find_work_item(work_item_id),
        sentry_employee=service.find_employee_by_position("QA_ENGINEER"),
        patch_artifact=patch_0,
        ai_client=review_0_ai,
        attempt_number=0,
    )

    # Revision attempting path escape
    escape_ai = SequenceMockAI([{
        "summary": "Malicious revision",
        "changes": [{"path": "../outside.py", "operation": "create", "content": "MALICIOUS=1\n"}],
        "requested_tests": [],
    }])

    with pytest.raises(PathSecurityError, match="strictly denied"):
        service.execute_revision(work_item_id, ai_client=escape_ai)


def test_12_router_revision_continue_endpoint(temp_ledger_db: Path, sandbox_manager: SandboxManager):
    """Test API endpoint POST /api/workforce/tasks/{work_item_id}/revision/continue and GET revisions."""
    from fastapi.testclient import TestClient
    from main import app
    from dependencies import get_copilot_ai_client, get_workforce_service

    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="Router Revision Org", ledger=ledger)
    service.execution_adapter.sandbox_manager = sandbox_manager

    router_ai = SequenceMockAI([
        # Coding fix
        {
            "summary": "Fixed R value to 2",
            "changes": [{"path": "CORE-SERVICES/r_test.py", "operation": "modify", "content": "R=2\n"}],
            "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_r_test.py"}],
        },
        # SENTRY review
        {
            "decision": "APPROVE_TECHNICAL",
            "summary": "All tests pass",
            "findings": [],
            "risks": [],
            "recommended_action": "Approved",
        },
    ])

    # Override dependencies
    app.dependency_overrides[get_workforce_service] = lambda: service
    app.dependency_overrides[get_copilot_ai_client] = lambda: router_ai

    try:
        client = TestClient(app)

        assign_res = service.assign_task(
            title="Router Revision Task",
            position_id="BACKEND_ENGINEER",
        )
        work_item_id = assign_res["work_item"]["work_item_id"]

        # Initial coding
        initial_ai = SequenceMockAI([{
            "summary": "Initial code",
            "changes": [
                {"path": "CORE-SERVICES/r_test.py", "operation": "create", "content": "R=1\n"},
                {"path": "CORE-SERVICES/test_r_test.py", "operation": "create", "content": "from r_test import R\ndef test_r(): assert R == 2\n"},
            ],
            "requested_tests": [{"kind": "PYTEST", "target": "CORE-SERVICES/test_r_test.py"}],
        }])
        patch_0 = service.execute_task(work_item_id, ai_client=initial_ai)

        review_0_ai = SequenceMockAI([{
            "decision": "REQUEST_CHANGES",
            "summary": "Test failed",
            "findings": ["Assertion error"],
            "risks": [],
            "recommended_action": "Fix R value",
        }])
        service.execution_adapter._perform_sentry_review(
            work_item=service.find_work_item(work_item_id),
            sentry_employee=service.find_employee_by_position("QA_ENGINEER"),
            patch_artifact=patch_0,
            ai_client=review_0_ai,
            attempt_number=0,
        )

        # Check eligibility endpoint
        elig_resp = client.get(f"/api/workforce/tasks/{work_item_id}/revision/eligibility")
        assert elig_resp.status_code == 200
        elig_data = elig_resp.json()
        assert elig_data["eligible"] is True
        assert elig_data["max_revisions"] == 2
        assert elig_data["revision_count"] == 0

        # Call continue endpoint
        post_resp = client.post(f"/api/workforce/tasks/{work_item_id}/revision/continue")
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["status"] == "APPROVED"
        assert post_data["attempt_number"] == 1

        # Check list revisions endpoint
        revs_resp = client.get(f"/api/workforce/tasks/{work_item_id}/revisions")
        assert revs_resp.status_code == 200
        revs_data = revs_resp.json()
        assert len(revs_data) == 1
        assert revs_data[0]["attempt_number"] == 1
        assert revs_data[0]["status"] == "COMPLETED"
    finally:
        app.dependency_overrides.clear()
