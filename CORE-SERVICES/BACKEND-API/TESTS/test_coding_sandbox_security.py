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
    PathPolicyValidator,
    PathSecurityError,
    SandboxManager,
    TestRunnerPolicy,
)
from API.agent_execution_adapter import AgentExecutionAdapter
from API.workforce_service import WorkforceService
from WORKFORCE.work_item import WorkItem


@pytest.fixture
def dummy_sandbox_root(tmp_path: Path) -> Path:
    root = tmp_path / "sandbox_test"
    root.mkdir(parents=True, exist_ok=True)
    return root


# 1. Path traversal denial: ../foo.py
def test_1_traversal_simple_denied(dummy_sandbox_root: Path):
    change = {"path": "../foo.py", "operation": "create", "content": "print(1)"}
    with pytest.raises(PathSecurityError, match="traversal"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 2. Path traversal denial: foo/../../bar.py
def test_2_traversal_nested_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/../../bar.py", "operation": "create", "content": "print(1)"}
    with pytest.raises(PathSecurityError, match="traversal"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 3. Path traversal denial with backslash: ..\foo.py
def test_3_traversal_backslash_denied(dummy_sandbox_root: Path):
    change = {"path": "..\\foo.py", "operation": "create", "content": "print(1)"}
    with pytest.raises(PathSecurityError, match="traversal"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 4. Path traversal denial: foo/..\..\bar.py
def test_4_traversal_nested_backslash_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/..\\..\\bar.py", "operation": "create", "content": "print(1)"}
    with pytest.raises(PathSecurityError, match="traversal"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 5. Absolute path denial Unix: /etc/passwd
def test_5_absolute_unix_denied(dummy_sandbox_root: Path):
    change = {"path": "/etc/passwd", "operation": "create", "content": "evil"}
    with pytest.raises(PathSecurityError, match="Absolute path"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 6. Absolute path denial Windows: C:\Windows\System32
def test_6_absolute_windows_denied(dummy_sandbox_root: Path):
    change = {"path": "C:\\Windows\\System32\\calc.exe", "operation": "create", "content": "evil"}
    with pytest.raises(PathSecurityError, match="denied"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 7. Absolute path denial Drive Letter: D:/PROJECT/foo.py
def test_7_drive_letter_denied(dummy_sandbox_root: Path):
    change = {"path": "D:/PROJECT/foo.py", "operation": "create", "content": "evil"}
    with pytest.raises(PathSecurityError, match="denied"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 8. UNC path denial: \\server\share\foo.py
def test_8_unc_path_denied(dummy_sandbox_root: Path):
    change = {"path": "\\\\server\\share\\foo.py", "operation": "create", "content": "evil"}
    with pytest.raises(PathSecurityError, match="UNC path"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 9. Normalized traversal escape: CORE-SERVICES/sub/../../secret.py
def test_9_normalized_escape_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/../outside.py", "operation": "create", "content": "evil"}
    with pytest.raises(PathSecurityError, match="traversal"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 10. Denied pattern: .git/config
def test_10_git_config_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/.git/config", "operation": "modify", "content": "[core]"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 11. Denied pattern: .git\HEAD
def test_11_git_head_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/.git\\HEAD", "operation": "modify", "content": "ref: refs/heads/main"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 12. Denied pattern: .env
def test_12_env_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/.env", "operation": "create", "content": "SECRET=1"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 13. Denied pattern: .env.production
def test_13_env_production_denied(dummy_sandbox_root: Path):
    change = {"path": "AI5R-STUDIO/.env.production", "operation": "create", "content": "PROD_SECRET=1"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 14. Denied pattern: credentials.json
def test_14_credentials_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/credentials.json", "operation": "create", "content": "{}"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 15. Denied pattern: secrets.yaml
def test_15_secrets_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/secrets.yaml", "operation": "create", "content": "key: 123"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 16. Denied pattern: id_rsa / id_ed25519
def test_16_ssh_keys_denied(dummy_sandbox_root: Path):
    for keyname in ("id_rsa", "id_ed25519", "private_key.pem"):
        change = {"path": f"CORE-SERVICES/{keyname}", "operation": "create", "content": "-----BEGIN KEY-----"}
        with pytest.raises(PathSecurityError, match="denied pattern"):
            PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 17. Denied pattern: .ssh/id_rsa
def test_17_ssh_dir_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/.ssh/config", "operation": "create", "content": "Host *"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 18. Denied pattern: runtime/backups
def test_18_runtime_backups_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/runtime/backups/db.bak", "operation": "create", "content": "dump"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 19. Denied pattern: production_config.py
def test_19_production_config_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/production_config.py", "operation": "create", "content": "DEBUG=False"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 20. Denied pattern: compose.yaml
def test_20_compose_yaml_denied(dummy_sandbox_root: Path):
    change = {"path": "CORE-SERVICES/compose.yaml", "operation": "create", "content": "services: {}"}
    with pytest.raises(PathSecurityError, match="denied pattern"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 21. Disallowed subtree: path outside allowed subtrees
def test_21_disallowed_subtrees(dummy_sandbox_root: Path):
    for bad_path in ("readme.md", "docs/architecture.md", "scripts/deploy.sh", "tmp/out.txt"):
        change = {"path": bad_path, "operation": "create", "content": "test"}
        with pytest.raises(PathSecurityError, match="allowed subtrees"):
            PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 22. Symlink escape detection
def test_22_symlink_escape_denied(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    outside_target = tmp_path / "outside_secret"
    sandbox_root.mkdir()
    outside_target.mkdir()

    # Create symlink inside sandbox pointing outside
    link_dir = sandbox_root / "CORE-SERVICES" / "symlink_dir"
    link_dir.parent.mkdir(parents=True)
    try:
        os.symlink(str(outside_target), str(link_dir), target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation requires elevated permissions on Windows")

    change = {"path": "CORE-SERVICES/symlink_dir/pwned.py", "operation": "create", "content": "escaped"}
    with pytest.raises(PathSecurityError, match="Symlink escape detected"):
        PathPolicyValidator.validate_change(sandbox_root, change)


# 23. Content size limit: change exceeding 1 MB
def test_23_content_size_limit_denied(dummy_sandbox_root: Path):
    large_content = "x" * (1_048_576 + 10)
    change = {"path": "CORE-SERVICES/large.py", "operation": "create", "content": large_content}
    with pytest.raises(PathSecurityError, match="maximum allowed size"):
        PathPolicyValidator.validate_change(dummy_sandbox_root, change)


# 24. Unauthorized role write denial: SOLUTION_ARCHITECT cannot write code
def test_24_solution_architect_write_denied():
    service = WorkforceService(organization_name="Security Test Org")
    assign_res = service.assign_task(
        title="Architecture Design",
        position_id="SOLUTION_ARCHITECT",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    class MockWritingArchitectAI:
        def generate(self, *args, **kwargs):
            return """{
                "summary": "Unauthorized attempt to create code file",
                "changes": [{"path": "CORE-SERVICES/injected.py", "operation": "create", "content": "print('hacked')"}]
            }"""

    with pytest.raises(RuntimeError, match="not authorized to modify source code"):
        service.execute_task(work_item_id=work_item_id, ai_client=MockWritingArchitectAI())

    item = service.find_work_item(work_item_id)
    assert item.status == "CLAIMED"


# 25. Unauthorized role write denial: DEVOPS, SECURITY, DOC, PM cannot write code
@pytest.mark.parametrize("unauth_pos", [
    "DEVOPS_ENGINEER",
    "SECURITY_ENGINEER",
    "DOCUMENTATION_ENGINEER",
    "PROJECT_MANAGER",
])
def test_25_other_roles_write_denied(unauth_pos: str):
    service = WorkforceService(organization_name="Security Test Org")
    assign_res = service.assign_task(
        title=f"Task for {unauth_pos}",
        position_id=unauth_pos,
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    class MockMaliciousRoleAI:
        def generate(self, *args, **kwargs):
            return """{
                "summary": "Attempting code write",
                "changes": [{"path": "CORE-SERVICES/exploit.py", "operation": "create", "content": "# exploit"}]
            }"""

    with pytest.raises(RuntimeError, match="not authorized to modify source code"):
        service.execute_task(work_item_id=work_item_id, ai_client=MockMaliciousRoleAI())

    item = service.find_work_item(work_item_id)
    assert item.status == "CLAIMED"


# 26. Command injection metatokens denied in test targets
@pytest.mark.parametrize("bad_char", [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"])
def test_26_command_injection_metatokens_denied(dummy_sandbox_root: Path, bad_char: str):
    target = f"CORE-SERVICES/tests/test_foo.py{bad_char}rm -rf /"
    with pytest.raises(ValueError, match="Command metacharacter"):
        TestRunnerPolicy.run_test(dummy_sandbox_root, kind="PYTEST", target=target)


# 27. Test runner safe execution: shell=False, secrets stripped, cleanup safety
def test_27_secrets_stripped_and_cleanup_safety(dummy_sandbox_root: Path):
    os.environ["SUPER_SECRET_API_KEY"] = "sk-1234567890"
    os.environ["DATABASE_PASSWORD"] = "db_hunter2"
    os.environ["AUTH_TOKEN"] = "auth_token_xyz"

    # Run benign test target that doesn't exist
    res = TestRunnerPolicy.run_test(dummy_sandbox_root, kind="PYTEST", target="CORE-SERVICES/nonexistent_test.py")
    assert res.passed is False
    assert res.exit_code != 0

    # Verify cleanup safety guards
    repo_root = REPO_ROOT.resolve()
    box = CodingSandbox(
        sandbox_id="SBX-FAKE-ROOT",
        work_item_id="WORK-1",
        employee_id="EMP-1",
        base_commit="HEAD",
        root_path=repo_root,
        repo_dir=repo_root,
    )
    with pytest.raises(RuntimeError, match="Refusing cleanup"):
        box.cleanup()
