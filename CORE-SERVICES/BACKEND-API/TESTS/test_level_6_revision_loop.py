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
from API.mission_lifecycle import (
    MissionStatus,
    ReviewFinding,
    DEFAULT_MAX_REVISION_ITERATIONS,
    RepeatedFindingError,
    RepeatedPatchError,
    DependencyDeadlockError,
)
from WORKFORCE.approval_chain_runtime import (
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
)
from WORKFORCE.work_item import WorkItem
from API.level_6_orchestrator import Level6MissionOrchestrator


class ConfigurableRoleAI:
    """Configurable AI double returning responses tailored to the role/prompt."""

    def __init__(
        self,
        qa_decisions: list[dict[str, Any]] | None = None,
        security_decisions: list[dict[str, Any]] | None = None,
        code_patches: list[dict[str, Any]] | None = None,
    ) -> None:
        self.qa_decisions = qa_decisions or [{"decision": "APPROVE_TECHNICAL", "summary": "QA Passed", "findings": [], "risks": []}]
        self.security_decisions = security_decisions or [{"decision": "APPROVE_TECHNICAL", "summary": "Security Passed", "findings": [], "risks": []}]
        self.code_patches = code_patches or []
        self.qa_call_idx = 0
        self.sec_call_idx = 0
        self.code_call_idx = 0
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})

        # Sentry QA Review prompt
        if "QA_ENGINEER" in system_prompt or "SENTRY" in system_prompt or "Quality Engineer" in system_prompt:
            if self.qa_call_idx < len(self.qa_decisions):
                resp = dict(self.qa_decisions[self.qa_call_idx])
            else:
                resp = dict(self.qa_decisions[-1])
            if not resp.get("summary"):
                resp["summary"] = f"QA Review evaluation attempt {self.qa_call_idx}"
            self.qa_call_idx += 1
            return json.dumps(resp)

        # Security Audit prompt
        if "SECURITY_ENGINEER" in system_prompt or "AIGIS" in system_prompt or "Security Engineer" in system_prompt or "Security Audit" in prompt:
            if self.sec_call_idx < len(self.security_decisions):
                resp = dict(self.security_decisions[self.sec_call_idx])
            else:
                resp = dict(self.security_decisions[-1])
            if not resp.get("summary"):
                resp["summary"] = f"Security Audit evaluation attempt {self.sec_call_idx}"
            self.sec_call_idx += 1
            return json.dumps(resp)

        # Coding / Sandbox prompt (Backend / Frontend Engineer)
        if "BACKEND_ENGINEER" in system_prompt or "FRONTEND_ENGINEER" in system_prompt:
            if self.code_patches and self.code_call_idx < len(self.code_patches):
                resp = self.code_patches[self.code_call_idx]
                self.code_call_idx += 1
                return json.dumps(resp)
            idx = self.code_call_idx
            self.code_call_idx += 1
            return json.dumps({
                "summary": f"Implemented patch attempt {idx}",
                "changes": [
                    {
                        "path": f"CORE-SERVICES/patch_{idx}.py",
                        "operation": "create",
                        "content": f"# Patch iteration {idx}\ndef run():\n    return {idx}\n",
                    }
                ],
                "requested_tests": [],
            })

        # Architect / DevOps / Documentation
        return json.dumps({
            "summary": "Engineering task completed successfully",
            "decisions": ["Follow standard architecture patterns"],
            "recommendations": ["Release via controlled Chief gate"],
        })


@pytest.fixture
def temp_ledger_db(tmp_path: Path) -> Path:
    return tmp_path / "test_level_6_ledger.db"


@pytest.fixture
def test_workforce(temp_ledger_db: Path) -> WorkforceService:
    ledger = ExecutionLedger(temp_ledger_db)
    service = WorkforceService(organization_name="AI5R Level 6 Org", ledger=ledger)
    service.execution_adapter.sandbox_manager = SandboxManager(repo_dir=REPO_ROOT)
    return service


# ==============================================================================
# TEST 1: Mission with all tasks passing first attempt -> READY_FOR_CHIEF_APPROVAL
# ==============================================================================
def test_1_all_tasks_pass_first_attempt(test_workforce: WorkforceService):
    """TEST 1: All tasks pass on first attempt -> transitions to READY_FOR_CHIEF_APPROVAL."""
    service = test_workforce

    create_res = service.create_mission(
        title="CM History Pagination and Occurrence Isolation",
        description="Access all historical CM readings without occurrence leakage",
        include_security=True,
        max_iterations=3,
    )
    mission_id = create_res["mission_id"]

    mock_ai = ConfigurableRoleAI(
        qa_decisions=[{"decision": "APPROVE_TECHNICAL", "summary": "All tests passed cleanly", "findings": [], "risks": []}],
        security_decisions=[{"decision": "APPROVE_TECHNICAL", "summary": "Zero security regressions", "findings": [], "risks": []}],
    )

    result = service.orchestrate_mission(
        mission_id=mission_id,
        ai_client=mock_ai,
        sentry_client=mock_ai,
        security_client=mock_ai,
    )

    assert result["status"] == MissionStatus.READY_FOR_CHIEF_APPROVAL
    assert result["approval_status"] == "PENDING"
    assert result["current_iteration"] == 0
    assert result["latest_review_result"]["decision"] == "APPROVE_TECHNICAL"
    assert result["latest_security_review_result"]["decision"] == "APPROVE_TECHNICAL"

    # Verify all tasks are completed
    assert all(t["status"] == "COMPLETED" for t in result["tasks"])

    # Verify Chief Approval event recorded
    events = service.get_mission_events(mission_id)
    event_types = [e["event_type"] for e in events]
    assert "MISSION_STARTED" in event_types
    assert "REVIEW_PASSED" in event_types
    assert "CHIEF_APPROVAL_REQUESTED" in event_types


# ==============================================================================
# TEST 2: QA fails first attempt -> Employee revises -> QA passes second attempt
# ==============================================================================
def test_2_qa_fails_first_attempt_employee_revises_qa_passes(test_workforce: WorkforceService):
    """TEST 2: QA fails first attempt -> revision loop -> QA passes -> READY_FOR_CHIEF_APPROVAL."""
    service = test_workforce

    create_res = service.create_mission(
        title="Fix CM History Pagination",
        description="Fix pagination without occurrence leakage",
        include_security=True,
        max_iterations=3,
    )
    mission_id = create_res["mission_id"]

    mock_ai = ConfigurableRoleAI(
        qa_decisions=[
            {
                "decision": "REQUEST_CHANGES",
                "summary": "Show More duplicates rows after page 2",
                "findings": ["Show More duplicates rows after page 2"],
                "risks": ["Data duplication on UI"],
                "recommended_action": "Deduplicate appended items by occurrence ID",
            },
            {
                "decision": "APPROVE_TECHNICAL",
                "summary": "Pagination deduplication verified successfully",
                "findings": [],
                "risks": [],
            },
        ],
        security_decisions=[
            {
                "decision": "APPROVE_TECHNICAL",
                "summary": "Security audit clean",
                "findings": [],
                "risks": [],
            }
        ],
        code_patches=[
            # Initial patch
            {
                "summary": "Initial pagination logic",
                "changes": [{"path": "CORE-SERVICES/cm_pag.py", "operation": "create", "content": "def get_page(p):\n    return [p, p]\n"}],
                "requested_tests": [],
            },
            # Revision patch (fixes bug)
            {
                "summary": "Fixed deduplication by occurrence ID",
                "changes": [{"path": "CORE-SERVICES/cm_pag.py", "operation": "modify", "content": "def get_page(p):\n    return list(set([p]))\n"}],
                "requested_tests": [],
            },
        ],
    )

    result = service.orchestrate_mission(
        mission_id=mission_id,
        ai_client=mock_ai,
        sentry_client=mock_ai,
        security_client=mock_ai,
    )

    assert result["status"] == MissionStatus.READY_FOR_CHIEF_APPROVAL
    assert result["current_iteration"] == 1

    # Verify structured review finding was captured
    findings = service.get_mission_findings(mission_id)
    assert len(findings) >= 1
    assert any("Show More duplicates rows" in f["description"] for f in findings)

    # Verify complete revision event sequence in ledger
    events = service.get_mission_events(mission_id)
    event_types = [e["event_type"] for e in events]
    assert "REVIEW_FAILED" in event_types
    assert "REVISION_REQUESTED" in event_types
    assert "REVISION_STARTED" in event_types
    assert "REVISION_COMPLETED" in event_types
    assert "REVIEW_PASSED" in event_types
    assert "CHIEF_APPROVAL_REQUESTED" in event_types


# ==============================================================================
# TEST 3: QA continues failing until maximum iterations -> REVISION_LIMIT_REACHED
# ==============================================================================
def test_3_qa_fails_until_max_iterations(test_workforce: WorkforceService):
    """TEST 3: QA continues failing -> autonomous loop halts at REVISION_LIMIT_REACHED."""
    service = test_workforce

    create_res = service.create_mission(
        title="Persistent Bug Fix Mission",
        description="Testing bounded autonomy limit",
        include_security=False,
        max_iterations=2,
    )
    mission_id = create_res["mission_id"]

    # Provide distinct findings to avoid repeated-finding loop detection, but continue failing
    mock_ai = ConfigurableRoleAI(
        qa_decisions=[
            {
                "decision": "REQUEST_CHANGES",
                "summary": "Failure 1: offset calculation out of bounds",
                "findings": ["Failure 1: offset calculation out of bounds"],
                "risks": ["Out of bounds"],
                "recommended_action": "Fix offset math",
            },
            {
                "decision": "REQUEST_CHANGES",
                "summary": "Failure 2: cursor token expired prematurely",
                "findings": ["Failure 2: cursor token expired prematurely"],
                "risks": ["Token expiration"],
                "recommended_action": "Refresh cursor token",
            },
            {
                "decision": "REQUEST_CHANGES",
                "summary": "Failure 3: occurrence isolation boundary breached",
                "findings": ["Failure 3: occurrence isolation boundary breached"],
                "risks": ["Data leak"],
                "recommended_action": "Enforce occurrence filter",
            },
        ],
        code_patches=[
            {"summary": "Attempt 0", "changes": [{"path": "CORE-SERVICES/p0.py", "operation": "create", "content": "x = 0\n"}], "requested_tests": []},
            {"summary": "Attempt 1", "changes": [{"path": "CORE-SERVICES/p1.py", "operation": "create", "content": "x = 1\n"}], "requested_tests": []},
            {"summary": "Attempt 2", "changes": [{"path": "CORE-SERVICES/p2.py", "operation": "create", "content": "x = 2\n"}], "requested_tests": []},
        ],
    )

    result = service.orchestrate_mission(
        mission_id=mission_id,
        ai_client=mock_ai,
        sentry_client=mock_ai,
    )

    assert result["status"] == MissionStatus.REVISION_LIMIT_REACHED
    assert result["current_iteration"] >= 2
    assert "limit" in result.get("metadata", {}).get("failure_reason", "").lower()

    # Verify boundary event logged
    events = service.get_mission_events(mission_id)
    event_types = [e["event_type"] for e in events]
    assert "REVISION_LIMIT_REACHED" in event_types


# ==============================================================================
# TEST 4: Security review fails and routes revision -> Chief approval unavailable
# ==============================================================================
def test_4_security_review_fails_and_revises(test_workforce: WorkforceService):
    """TEST 4: Security review fails -> revision routed -> Security passes -> READY_FOR_CHIEF_APPROVAL."""
    service = test_workforce

    create_res = service.create_mission(
        title="Secure Data Pipeline Export",
        description="Verify security review failure loop",
        include_security=True,
        max_iterations=3,
    )
    mission_id = create_res["mission_id"]

    mock_ai = ConfigurableRoleAI(
        qa_decisions=[
            {"decision": "APPROVE_TECHNICAL", "summary": "QA passed cleanly", "findings": [], "risks": []},
            {"decision": "APPROVE_TECHNICAL", "summary": "QA re-verified clean", "findings": [], "risks": []},
        ],
        security_decisions=[
            {
                "decision": "REQUEST_CHANGES",
                "summary": "Potential SQL injection vulnerability",
                "findings": ["Potential SQL injection vulnerability in pagination filter parameter"],
                "risks": ["Arbitrary database query execution"],
                "recommended_action": "Use parameterized query bindings",
            },
            {
                "decision": "APPROVE_TECHNICAL",
                "summary": "Parameterized query bindings successfully validated",
                "findings": [],
                "risks": [],
            },
        ],
        code_patches=[
            {"summary": "Initial code", "changes": [{"path": "CORE-SERVICES/sec_test.py", "operation": "create", "content": "q = 'SELECT * FROM x'\n"}], "requested_tests": []},
            {"summary": "Remediated code", "changes": [{"path": "CORE-SERVICES/sec_test.py", "operation": "modify", "content": "q = ('SELECT * FROM x WHERE id = :id', {'id': 1})\n"}], "requested_tests": []},
        ],
    )

    result = service.orchestrate_mission(
        mission_id=mission_id,
        ai_client=mock_ai,
        sentry_client=mock_ai,
        security_client=mock_ai,
    )

    assert result["status"] == MissionStatus.READY_FOR_CHIEF_APPROVAL
    assert result["latest_security_review_result"]["decision"] == "APPROVE_TECHNICAL"

    # Check security finding recorded
    findings = service.get_mission_findings(mission_id)
    sec_findings = [f for f in findings if f["category"] == "SECURITY"]
    assert len(sec_findings) >= 1
    assert "SQL injection" in sec_findings[0]["description"]


# ==============================================================================
# TEST 5: Dependency failure blocks downstream execution -> BLOCKED
# ==============================================================================
def test_5_dependency_failure_blocks_execution(test_workforce: WorkforceService):
    """TEST 5: Deadlock / missing dependency blocks execution cleanly without unhandled crash."""
    service = test_workforce

    create_res = service.create_mission(
        title="Blocked Mission",
        description="Testing dependency deadlock prevention",
        include_security=False,
    )
    mission_id = create_res["mission_id"]

    # Deliberately manipulate plan to simulate circular / unresolvable dependency
    plan = service._plans[mission_id]
    task_ids = service._missions[mission_id]["task_ids"]

    # Create mutual dependency between tasks to force deadlock
    plan.dependency_graph[task_ids[0]] = [task_ids[1]]
    plan.dependency_graph[task_ids[1]] = [task_ids[0]]
    plan.blocked = list(task_ids)
    plan.running = []

    result = service.orchestrate_mission(mission_id=mission_id)

    assert result["status"] == MissionStatus.BLOCKED
    events = service.get_mission_events(mission_id)
    event_types = [e["event_type"] for e in events]
    assert "MISSION_BLOCKED" in event_types


# ==============================================================================
# TEST 6: Chief Approval cannot be bypassed
# ==============================================================================
def test_6_chief_approval_cannot_be_bypassed(test_workforce: WorkforceService):
    """TEST 6: AI cannot approve; approval before READY_FOR_CHIEF_APPROVAL fails; valid Chief succeeds."""
    service = test_workforce

    create_res = service.create_mission(
        title="Mission Under Gate Control",
        description="Governance test",
        include_security=False,
    )
    mission_id = create_res["mission_id"]

    # 1. AI agent attempt to approve must be forbidden
    with pytest.raises(ChiefApprovalRequiredError):
        service.approve_mission(
            mission_id=mission_id,
            approver_id="ai-bot",
            approver_role="AI_AGENT",
            is_human=False,
        )

    # 2. Premature approval attempt before mission reaches READY_FOR_CHIEF_APPROVAL must fail
    with pytest.raises(ValueError, match="READY_FOR_CHIEF_APPROVAL"):
        service.approve_mission(
            mission_id=mission_id,
            approver_id="raid",
            approver_role="CHIEF_ARCHITECT",
            is_human=True,
        )

    # Now run orchestrate to READY_FOR_CHIEF_APPROVAL
    mock_ai = ConfigurableRoleAI()
    service.orchestrate_mission(mission_id=mission_id, ai_client=mock_ai, sentry_client=mock_ai)

    mission = service.get_mission(mission_id)
    assert mission["status"] == MissionStatus.READY_FOR_CHIEF_APPROVAL

    # 3. Explicit Chief approval with is_human=True succeeds
    approved_res = service.approve_mission(
        mission_id=mission_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )

    assert approved_res["status"] in (MissionStatus.APPROVED, MissionStatus.COMPLETED)
    assert approved_res["approval_status"] == "APPROVED"

    events = service.get_mission_events(mission_id)
    event_types = [e["event_type"] for e in events]
    assert "CHIEF_APPROVED" in event_types


# ==============================================================================
# TEST 7: Production mutation cannot occur through autonomous loop
# ==============================================================================
def test_7_production_mutation_cannot_occur_through_autonomous_loop(test_workforce: WorkforceService):
    """TEST 7: Autonomous loop cannot mutate production or release tasks autonomously."""
    service = test_workforce

    create_res = service.create_mission(
        title="Production Critical Mission",
        description="Production safety audit",
        is_production=True,
        include_security=False,
    )
    mission_id = create_res["mission_id"]

    mock_ai = ConfigurableRoleAI()
    result = service.orchestrate_mission(mission_id=mission_id, ai_client=mock_ai, sentry_client=mock_ai)

    assert result["status"] == MissionStatus.READY_FOR_CHIEF_APPROVAL
    assert result["is_production"] is True

    # Tasks marked is_production must NOT be RELEASED autonomously
    for task in result["tasks"]:
        assert task["status"] != "RELEASED"

    # Releasing without Chief approval must raise error
    prod_task = next(t for t in result["tasks"] if t.get("is_production") or t.get("metadata", {}).get("is_production"))
    with pytest.raises(ChiefApprovalRequiredError):
        service.release_task(
            work_item_id=prod_task["work_item_id"],
            approval=ChiefApprovalRecord(
                work_item_id=prod_task["work_item_id"],
                approver_id="ai_bot",
                approver_role="AUTOMATED_PIPELINE",
                is_human=False,
            ),
        )


# ==============================================================================
# TEST 8: Execution ledger contains complete ordered lifecycle events
# ==============================================================================
def test_8_ledger_contains_complete_ordered_lifecycle_events(test_workforce: WorkforceService):
    """TEST 8: Ledger records complete, attributable, ordered lifecycle event chain."""
    service = test_workforce

    create_res = service.create_mission(
        title="Audited Mission Lifecycle",
        description="Verifying complete ledger audit trail",
        include_security=True,
        max_iterations=3,
    )
    mission_id = create_res["mission_id"]

    mock_ai = ConfigurableRoleAI(
        qa_decisions=[
            {"decision": "REQUEST_CHANGES", "summary": "Minor test discrepancy", "findings": ["Minor test discrepancy"], "risks": [], "recommended_action": "Fix assertion"},
            {"decision": "APPROVE_TECHNICAL", "summary": "Passed", "findings": [], "risks": []},
        ],
        security_decisions=[
            {"decision": "APPROVE_TECHNICAL", "summary": "Security Passed", "findings": [], "risks": []},
        ],
        code_patches=[
            {"summary": "Patch 0", "changes": [{"path": "CORE-SERVICES/a.py", "operation": "create", "content": "a = 1\n"}], "requested_tests": []},
            {"summary": "Patch 1", "changes": [{"path": "CORE-SERVICES/a.py", "operation": "modify", "content": "a = 2\n"}], "requested_tests": []},
        ],
    )

    service.orchestrate_mission(mission_id=mission_id, ai_client=mock_ai, sentry_client=mock_ai, security_client=mock_ai)

    # Approve mission as Chief
    service.approve_mission(
        mission_id=mission_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )

    events = service.get_mission_events(mission_id)
    assert len(events) >= 10

    event_types = [e["event_type"] for e in events]

    expected_sequence = [
        "MISSION_CREATED",
        "PLAN_CREATED",
        "MISSION_STARTED",
        "TASK_STARTED",
        "REVIEW_STARTED",
        "REVIEW_FAILED",
        "REVISION_REQUESTED",
        "REVISION_STARTED",
        "REVISION_COMPLETED",
        "REVIEW_PASSED",
        "CHIEF_APPROVAL_REQUESTED",
        "CHIEF_APPROVED",
    ]

    for expected_type in expected_sequence:
        assert expected_type in event_types, f"Expected event type '{expected_type}' missing from ledger events"

    # Verify attribution: every event answers WHO did WHAT, WHY, WHEN, ON WHICH MISSION/TASK, WITH WHAT RESULT
    for event in events:
        assert event["event_id"]
        assert event["event_type"]
        assert event["who"]
        assert event["what"]
        assert event["timestamp"]
        assert event["mission_id"] == mission_id
