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
    PatchArtifact,
    ReviewArtifact,
    SandboxManager,
    TestResult,
    TestRunnerPolicy,
)
from API.agent_execution_adapter import AgentExecutionAdapter
from API.workforce_service import WorkforceService
from WORKFORCE.approval_chain_runtime import (
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
)
from WORKFORCE.work_item import WorkItem


@pytest.fixture
def sandbox_manager() -> SandboxManager:
    return SandboxManager(repo_dir=REPO_ROOT)


# 1. SandboxManager.create_sandbox creates a real detached git worktree
def test_1_create_sandbox_detached_worktree(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-1", employee_id="EMP-FORGE")
    try:
        assert sandbox.sandbox_id.startswith("SBX-")
        assert sandbox.root_path.exists()
        assert (sandbox.root_path / ".git").exists()
        assert sandbox.status == "ACTIVE"
    finally:
        sandbox.cleanup()


# 2. Base commit matches current repo commit
def test_2_sandbox_immutable_base_commit(sandbox_manager: SandboxManager):
    expected_commit = sandbox_manager.get_current_base_commit()
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-2", employee_id="EMP-FORGE")
    try:
        assert sandbox.base_commit == expected_commit
    finally:
        sandbox.cleanup()


# 3. apply_changes creates new file in sandbox worktree
def test_3_apply_changes_create_file(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-3", employee_id="EMP-FORGE")
    try:
        rel_path = "CORE-SERVICES/sandbox_created_probe.py"
        applied = sandbox.apply_changes([{
            "path": rel_path,
            "operation": "create",
            "content": "# Sandbox Created Probe\nVALUE = 42\n",
        }])
        assert rel_path in applied
        full_path = sandbox.root_path / rel_path
        assert full_path.exists()
        assert "VALUE = 42" in full_path.read_text(encoding="utf-8")
    finally:
        sandbox.cleanup()


# 4. apply_changes modifies existing tracked file in sandbox
def test_4_apply_changes_modify_file(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-4", employee_id="EMP-FORGE")
    try:
        rel_path = "CORE-SERVICES/API/workforce_service.py"
        target_file = sandbox.root_path / rel_path
        assert target_file.exists()
        original_content = target_file.read_text(encoding="utf-8")

        new_content = original_content + "\n# Modified probe for test 4\n"
        sandbox.apply_changes([{
            "path": rel_path,
            "operation": "modify",
            "content": new_content,
        }])
        assert target_file.read_text(encoding="utf-8") == new_content
    finally:
        sandbox.cleanup()


# 5. apply_changes does NOT touch original repo worktree
def test_5_sandbox_isolation_preserves_repo(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-5", employee_id="EMP-FORGE")
    try:
        probe_path = "CORE-SERVICES/isolation_test_probe.txt"
        sandbox.apply_changes([{
            "path": probe_path,
            "operation": "create",
            "content": "isolated in sandbox only",
        }])
        assert (sandbox.root_path / probe_path).exists()
        # Original repository root must NOT contain probe_path
        assert not (REPO_ROOT / probe_path).exists()
    finally:
        sandbox.cleanup()
        assert not (REPO_ROOT / probe_path).exists()


# 6. generate_diff captures untracked new files (git add -N .)
def test_6_generate_diff_captures_untracked_new_files(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-6", employee_id="EMP-FORGE")
    try:
        rel_path = "CORE-SERVICES/brand_new_file.py"
        sandbox.apply_changes([{
            "path": rel_path,
            "operation": "create",
            "content": "def hello():\n    return 'world'\n",
        }])
        changed_files, diff_stat, git_diff = sandbox.generate_diff()
        assert rel_path in changed_files
        assert "def hello():" in git_diff
        assert "brand_new_file.py" in diff_stat
    finally:
        sandbox.cleanup()


# 7. generate_diff produces real git diff
def test_7_generate_diff_real_diff_output(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-7", employee_id="EMP-FORGE")
    try:
        rel_path = "CORE-SERVICES/diff_probe.py"
        sandbox.apply_changes([{
            "path": rel_path,
            "operation": "create",
            "content": "x = 100\n",
        }])
        _, _, git_diff = sandbox.generate_diff()
        assert "diff --git" in git_diff
        assert "+x = 100" in git_diff
    finally:
        sandbox.cleanup()


# 8. generate_diff produces real diff_stat
def test_8_generate_diff_stat(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-8", employee_id="EMP-FORGE")
    try:
        sandbox.apply_changes([{
            "path": "CORE-SERVICES/stat_probe.py",
            "operation": "create",
            "content": "line1\nline2\nline3\n",
        }])
        _, diff_stat, _ = sandbox.generate_diff()
        assert "stat_probe.py" in diff_stat
        assert "1 file changed" in diff_stat
    finally:
        sandbox.cleanup()


# 9. generate_diff truncates diff exceeding 64KB
def test_9_generate_diff_truncates_large_diff(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-9", employee_id="EMP-FORGE")
    try:
        # Create file with ~70KB content
        huge_content = "def big():\n" + ("    x = 1\n" * 7000)
        sandbox.apply_changes([{
            "path": "CORE-SERVICES/huge.py",
            "operation": "create",
            "content": huge_content,
        }])
        _, _, git_diff = sandbox.generate_diff()
        assert "[DIFF TRUNCATED: DISPLAY EXCEEDS 64KB LIMIT]" in git_diff
        assert len(git_diff.encode("utf-8")) <= 66_000
    finally:
        sandbox.cleanup()


# 10. run_tests executes PYTEST target and captures passing TestResult
def test_10_run_tests_pytest_passing(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-10", employee_id="EMP-FORGE")
    try:
        # Create a passing unit test in sandbox
        sandbox.apply_changes([
            {
                "path": "CORE-SERVICES/dummy_math.py",
                "operation": "create",
                "content": "def add(a, b): return a + b\n",
            },
            {
                "path": "CORE-SERVICES/test_dummy_math.py",
                "operation": "create",
                "content": "from dummy_math import add\ndef test_add(): assert add(2, 3) == 5\n",
            },
        ])
        results = sandbox.run_tests([{"kind": "PYTEST", "target": "CORE-SERVICES/test_dummy_math.py"}])
        assert len(results) == 1
        res = results[0]
        assert res.passed is True
        assert res.exit_code == 0
        assert res.duration >= 0.0
        assert res.timed_out is False
    finally:
        sandbox.cleanup()


# 11. run_tests executes PYTEST target and captures failing TestResult
def test_11_run_tests_pytest_failing(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-11", employee_id="EMP-FORGE")
    try:
        # Create a failing unit test in sandbox
        sandbox.apply_changes([
            {
                "path": "CORE-SERVICES/test_dummy_fail.py",
                "operation": "create",
                "content": "def test_fail(): assert 1 == 2\n",
            },
        ])
        results = sandbox.run_tests([{"kind": "PYTEST", "target": "CORE-SERVICES/test_dummy_fail.py"}])
        assert len(results) == 1
        res = results[0]
        assert res.passed is False
        assert res.exit_code != 0
        assert "assert 1 == 2" in (res.stdout_summary + res.stderr_summary)
    finally:
        sandbox.cleanup()


# 12. run_tests records duration and summaries
def test_12_run_tests_captures_duration_and_summaries(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-12", employee_id="EMP-FORGE")
    try:
        results = sandbox.run_tests([{"kind": "PYTEST", "target": "CORE-SERVICES/nonexistent.py"}])
        assert len(results) == 1
        res = results[0]
        assert isinstance(res.duration, float)
        assert res.test_result_id.startswith("TR-")
        assert res.command_id == "PYTEST"
    finally:
        sandbox.cleanup()


# 13. run_tests handles timeout
def test_13_run_tests_handles_timeout(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-13", employee_id="EMP-FORGE")
    try:
        # Create slow test
        sandbox.apply_changes([{
            "path": "CORE-SERVICES/test_slow.py",
            "operation": "create",
            "content": "import time\ndef test_slow(): time.sleep(5)\n",
        }])
        # Run with tiny timeout
        res = TestRunnerPolicy.run_test(sandbox.root_path, kind="PYTEST", target="CORE-SERVICES/test_slow.py", timeout=0.5)
        assert res.timed_out is True
        assert res.passed is False
        assert res.exit_code == 124
    finally:
        sandbox.cleanup()


# 14 & 15. cleanup removes worktree and directory, status CLEANED
def test_14_15_sandbox_cleanup(sandbox_manager: SandboxManager):
    sandbox = sandbox_manager.create_sandbox(work_item_id="WORK-TEST-14", employee_id="EMP-FORGE")
    path = sandbox.root_path
    assert path.exists()
    assert sandbox.status == "ACTIVE"

    sandbox.cleanup()
    assert sandbox.status == "CLEANED"
    assert not path.exists()


# 16 & 17. BACKEND_ENGINEER executes with changes producing PatchArtifact
def test_16_17_backend_engineer_produces_patch_artifact():
    service = WorkforceService(organization_name="Functional Test Org")
    assign_res = service.assign_task(
        title="Add Heartbeat Service",
        description="Implement heartbeat endpoint in CORE-SERVICES",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    class MockForgeAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Implemented heartbeat health check service.",
                "changes": [
                    {
                        "path": "CORE-SERVICES/heartbeat_probe.py",
                        "operation": "create",
                        "content": "def is_alive():\n    return True\n",
                    },
                    {
                        "path": "CORE-SERVICES/test_heartbeat_probe.py",
                        "operation": "create",
                        "content": "from heartbeat_probe import is_alive\ndef test_alive(): assert is_alive() is True\n",
                    }
                ],
                "requested_tests": [
                    {"kind": "PYTEST", "target": "CORE-SERVICES/test_heartbeat_probe.py"}
                ]
            })

    artifact = service.execute_task(work_item_id=work_item_id, ai_client=MockForgeAI())
    assert isinstance(artifact, PatchArtifact)
    assert artifact.status == "SUCCESS"
    assert "CORE-SERVICES/heartbeat_probe.py" in artifact.changed_files
    assert "def is_alive():" in artifact.git_diff
    assert len(artifact.test_results) == 1
    assert artifact.test_results[0].passed is True

    item = service.find_work_item(work_item_id)
    assert item.status == "COMPLETED"


# 18. FRONTEND_ENGINEER executes with changes producing PatchArtifact
def test_18_frontend_engineer_produces_patch_artifact():
    service = WorkforceService(organization_name="Functional Test Org")
    assign_res = service.assign_task(
        title="Build Status Badge Widget",
        position_id="FRONTEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    class MockCanvasAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Implemented StatusBadge React component.",
                "changes": [
                    {
                        "path": "AI5R-STUDIO/dashboard/src/StatusBadge.jsx",
                        "operation": "create",
                        "content": "export function StatusBadge({ status }) { return <span>{status}</span>; }\n",
                    }
                ],
                "requested_tests": []
            })

    artifact = service.execute_task(work_item_id=work_item_id, ai_client=MockCanvasAI())
    assert isinstance(artifact, PatchArtifact)
    assert artifact.role == "FRONTEND_ENGINEER"
    assert "AI5R-STUDIO/dashboard/src/StatusBadge.jsx" in artifact.changed_files
    assert "export function StatusBadge" in artifact.git_diff


# 19. PatchArtifact.to_dict schema compliance
def test_19_patch_artifact_schema_compliance():
    service = WorkforceService(organization_name="Functional Test Org")
    assign_res = service.assign_task(
        title="Quick Backend Patch",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    class MockAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Quick patch",
                "changes": [
                    {"path": "CORE-SERVICES/quick.py", "operation": "create", "content": "A = 1\n"}
                ],
                "requested_tests": []
            })

    artifact = service.execute_task(work_item_id=work_item_id, ai_client=MockAI())
    data = artifact.to_dict()
    assert data["artifact_id"].startswith("PATCH-")
    assert data["sandbox_id"].startswith("SBX-")
    assert "diff_stat" in data
    assert "git_diff" in data
    assert "test_results" in data
    assert "output" in data
    assert data["output"]["git_diff"] == data["git_diff"]


class DefaultAnalysisMockAI:
    def generate(self, *args, **kwargs):
        return json.dumps({
            "summary": "Completed analysis successfully.",
            "findings": ["Finding 1", "Finding 2"],
            "deliverables": "Deliverables documented.",
            "risks_and_considerations": ["Risk 1", "Risk 2"],
        })


# 20. SENTRY QA evaluates PatchArtifact and grants APPROVE_TECHNICAL when tests pass
def test_20_sentry_grants_approval_on_passing_tests():
    service = WorkforceService(organization_name="Functional Test Org")
    service.execution_adapter.ai_client = DefaultAnalysisMockAI()
    mission = service.create_mission(title="Feature with Full QA Pipeline")
    tasks = mission["tasks"]
    arch_task = next(t for t in tasks if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    backend_task = next(t for t in tasks if t["assigned_position_id"] == "BACKEND_ENGINEER")
    frontend_task = next(t for t in tasks if t["assigned_position_id"] == "FRONTEND_ENGINEER")
    qa_task = next(t for t in tasks if t["assigned_position_id"] == "QA_ENGINEER")

    # 1. Execute ARCH (read-only)
    service.execute_task(arch_task["work_item_id"])

    # 2. Execute BACKEND (produces PatchArtifact with passing test)
    class MockPassingBackendAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Implemented verified math helper.",
                "changes": [
                    {"path": "CORE-SERVICES/math_helper.py", "operation": "create", "content": "def square(n): return n * n\n"},
                    {"path": "CORE-SERVICES/test_math_helper.py", "operation": "create", "content": "from math_helper import square\ndef test_sq(): assert square(4) == 16\n"},
                ],
                "requested_tests": [
                    {"kind": "PYTEST", "target": "CORE-SERVICES/test_math_helper.py"}
                ]
            })

    patch_art = service.execute_task(backend_task["work_item_id"], ai_client=MockPassingBackendAI())
    assert isinstance(patch_art, PatchArtifact)
    assert patch_art.test_results[0].passed is True

    # Execute FRONTEND to unblock QA
    service.execute_task(frontend_task["work_item_id"])

    # 3. Execute SENTRY QA
    class MockSentryApprovingAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "decision": "APPROVE_TECHNICAL",
                "summary": "Code and tests passed. Clean implementation.",
                "findings": ["Unit tests cover positive cases", "Clean modular structure"],
                "risks": ["Integer overflow on massive inputs"],
                "recommended_action": "Proceed to Chief review"
            })

    review_art = service.execute_task(qa_task["work_item_id"], ai_client=MockSentryApprovingAI())
    assert isinstance(review_art, ReviewArtifact)
    assert review_art.decision == "APPROVE_TECHNICAL"
    assert review_art.test_evidence_reviewed["all_passed"] is True
    assert review_art.test_evidence_reviewed["failed_tests"] == 0
    assert review_art.reviewed_artifact_ids == [patch_art.artifact_id]


# 21 & 22. SENTRY truthfulness override: when tests fail, APPROVE_TECHNICAL overridden to REQUEST_CHANGES
def test_21_22_sentry_truthfulness_override_on_test_failure():
    service = WorkforceService(organization_name="Functional Test Org")
    service.execution_adapter.ai_client = DefaultAnalysisMockAI()
    mission = service.create_mission(title="Broken Patch Mission")
    tasks = mission["tasks"]
    arch_task = next(t for t in tasks if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    backend_task = next(t for t in tasks if t["assigned_position_id"] == "BACKEND_ENGINEER")
    frontend_task = next(t for t in tasks if t["assigned_position_id"] == "FRONTEND_ENGINEER")
    qa_task = next(t for t in tasks if t["assigned_position_id"] == "QA_ENGINEER")

    service.execute_task(arch_task["work_item_id"])

    # Backend creates failing test
    class MockFailingBackendAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Buggy patch with failing test.",
                "changes": [
                    {"path": "CORE-SERVICES/broken.py", "operation": "create", "content": "BROKEN = True\n"},
                    {"path": "CORE-SERVICES/test_broken.py", "operation": "create", "content": "def test_broken(): assert False\n"},
                ],
                "requested_tests": [
                    {"kind": "PYTEST", "target": "CORE-SERVICES/test_broken.py"}
                ]
            })

    patch_art = service.execute_task(backend_task["work_item_id"], ai_client=MockFailingBackendAI())
    assert patch_art.test_results[0].passed is False

    # Execute FRONTEND to unblock QA
    service.execute_task(frontend_task["work_item_id"])

    # SENTRY LLM attempts to claim APPROVE_TECHNICAL despite failing test
    class MockSentryLyingAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "decision": "APPROVE_TECHNICAL",
                "summary": "Looks great to me, approving anyway!",
                "findings": ["Everything is fine"],
                "risks": [],
                "recommended_action": "Ship it"
            })

    review_art = service.execute_task(qa_task["work_item_id"], ai_client=MockSentryLyingAI())
    assert isinstance(review_art, ReviewArtifact)
    # TRUTHFULNESS OVERRIDE ENFORCED!
    assert review_art.decision == "REQUEST_CHANGES"
    assert any("Automated test verification failed" in f for f in review_art.findings)
    assert review_art.test_evidence_reviewed["all_passed"] is False
    assert review_art.test_evidence_reviewed["failed_tests"] == 1


# 23. ReviewArtifact.to_dict schema compliance
def test_23_review_artifact_schema_compliance():
    review = ReviewArtifact(
        review_id="REV-12345",
        work_item_id="WORK-QA-1",
        employee_id="EMP-SENTRY",
        role="QA_ENGINEER",
        reviewed_artifact_ids=["PATCH-1"],
        decision="REQUEST_CHANGES",
        findings=["Issue with error handling"],
        risks=["Memory leak under load"],
        test_evidence_reviewed={"total_tests": 1, "passed_tests": 0, "failed_tests": 1},
        recommended_action="Refactor error handling",
        started_at="2026-09-16T00:00:00Z",
        completed_at="2026-09-16T00:01:00Z",
    )
    data = review.to_dict()
    assert data["review_id"] == "REV-12345"
    assert data["artifact_id"] == "REV-12345"
    assert data["decision"] == "REQUEST_CHANGES"
    assert "findings" in data["output"]
    assert "test_evidence_reviewed" in data


# 24. APPROVE_TECHNICAL does NOT bypass Human Chief Gate
def test_24_technical_approval_does_not_release_production():
    service = WorkforceService(organization_name="Functional Test Org")
    service.execution_adapter.ai_client = DefaultAnalysisMockAI()
    mission = service.create_mission(title="Production Payment Gateway", is_production=True)
    tasks = mission["tasks"]
    arch_task = next(t for t in tasks if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    backend_task = next(t for t in tasks if t["assigned_position_id"] == "BACKEND_ENGINEER")
    frontend_task = next(t for t in tasks if t["assigned_position_id"] == "FRONTEND_ENGINEER")
    qa_task = next(t for t in tasks if t["assigned_position_id"] == "QA_ENGINEER")
    devops_task = next(t for t in tasks if t["assigned_position_id"] == "DEVOPS_ENGINEER")

    service.execute_task(arch_task["work_item_id"])
    service.execute_task(backend_task["work_item_id"])
    service.execute_task(frontend_task["work_item_id"])

    # QA technically approves
    class MockSentryApproveAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "decision": "APPROVE_TECHNICAL",
                "summary": "Passed all tests.",
                "findings": [],
                "risks": [],
                "recommended_action": "Ready for Chief approval"
            })

    service.execute_task(qa_task["work_item_id"], ai_client=MockSentryApproveAI())

    # DevOps task completes
    service.execute_task(devops_task["work_item_id"])
    devops_item = service.find_work_item(devops_task["work_item_id"])
    assert devops_item.status == "COMPLETED"

    # Attempting release WITHOUT Chief approval MUST FAIL
    with pytest.raises(ChiefApprovalRequiredError, match="Human Chief approval is MISSING"):
        service.release_task(devops_task["work_item_id"])

    # Release with Human Chief approval succeeds
    chief_approval = ChiefApprovalRecord(
        work_item_id=devops_task["work_item_id"],
        approver_id="CHIEF-HUMAN",
        approver_role="CHIEF",
        is_human=True,
    )
    released_item = service.release_task(devops_task["work_item_id"], approval=chief_approval)
    assert released_item.status == "RELEASED"


# 25. WorkBoard transitions to COMPLETED after sandbox execution
def test_25_work_board_transitions_to_completed():
    service = WorkforceService(organization_name="Functional Test Org")
    assign_res = service.assign_task(
        title="Add Data Model",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    item = service.find_work_item(work_item_id)
    assert item.status == "CLAIMED"

    class MockAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Model added",
                "changes": [{"path": "CORE-SERVICES/model.py", "operation": "create", "content": "M=1"}],
                "requested_tests": []
            })

    service.execute_task(work_item_id, ai_client=MockAI())
    item_after = service.find_work_item(work_item_id)
    assert item_after.status == "COMPLETED"
    assert item_after.work_item_id in [c.work_item_id for c in service.work_board.completed_work_items()]


# 26. Full multi-agent mission flow
def test_26_full_mission_flow_arch_sandbox_qa_chief():
    service = WorkforceService(organization_name="Functional Test Org")
    service.execution_adapter.ai_client = DefaultAnalysisMockAI()
    mission = service.create_mission(title="Full Feature Rollout", is_production=True)
    plan = service._plans[mission["mission_id"]]

    tasks_by_pos = {t["assigned_position_id"]: t for t in mission["tasks"]}
    arch_id = tasks_by_pos["SOLUTION_ARCHITECT"]["work_item_id"]
    backend_id = tasks_by_pos["BACKEND_ENGINEER"]["work_item_id"]
    frontend_id = tasks_by_pos["FRONTEND_ENGINEER"]["work_item_id"]
    qa_id = tasks_by_pos["QA_ENGINEER"]["work_item_id"]
    devops_id = tasks_by_pos["DEVOPS_ENGINEER"]["work_item_id"]

    # Step 1: ARCH executes
    service.execute_task(arch_id)
    assert arch_id in plan.completed

    # Step 2: BACKEND executes in Sandbox
    class MockBackendAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "summary": "Engineered feature in sandbox with test",
                "changes": [
                    {"path": "CORE-SERVICES/feat.py", "operation": "create", "content": "FEAT = 1\n"},
                    {"path": "CORE-SERVICES/test_feat.py", "operation": "create", "content": "from feat import FEAT\ndef test_f(): assert FEAT == 1\n"},
                ],
                "requested_tests": [
                    {"kind": "PYTEST", "target": "CORE-SERVICES/test_feat.py"}
                ]
            })

    patch_art = service.execute_task(backend_id, ai_client=MockBackendAI())
    assert isinstance(patch_art, PatchArtifact)
    assert patch_art.test_results[0].passed is True

    # Step 2b: FRONTEND executes
    service.execute_task(frontend_id)

    # Step 3: SENTRY evaluates PatchArtifact
    class MockQAAI:
        def generate(self, *args, **kwargs):
            return json.dumps({
                "decision": "APPROVE_TECHNICAL",
                "summary": "Technical review passed. Verified in sandbox.",
                "findings": ["All automated tests passed"],
                "risks": [],
                "recommended_action": "Proceed"
            })

    review_art = service.execute_task(qa_id, ai_client=MockQAAI())
    assert isinstance(review_art, ReviewArtifact)
    assert review_art.decision == "APPROVE_TECHNICAL"

    # Step 4: DevOps executes
    service.execute_task(devops_id)

    # Step 5: Chief Approval required to release
    with pytest.raises(ChiefApprovalRequiredError):
        service.release_task(devops_id)

    chief_rec = ChiefApprovalRecord(
        work_item_id=devops_id,
        approver_id="CHIEF-HUMAN",
        approver_role="CHIEF",
        is_human=True,
    )
    released = service.release_task(devops_id, approval=chief_rec)
    assert released.status == "RELEASED"
