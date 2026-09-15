from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TestResult:
    """Canonical record of a real allowlisted test execution."""

    test_result_id: str
    command_id: str
    target: str
    exit_code: int
    passed: bool
    duration: float
    stdout_summary: str
    stderr_summary: str
    timed_out: bool = False
    __test__ = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_result_id": self.test_result_id,
            "command_id": self.command_id,
            "target": self.target,
            "exit_code": self.exit_code,
            "passed": self.passed,
            "duration": self.duration,
            "stdout_summary": self.stdout_summary,
            "stderr_summary": self.stderr_summary,
            "timed_out": self.timed_out,
        }


@dataclass
class PatchArtifact:
    """Canonical artifact generated from real sandbox file modifications and test executions."""

    artifact_id: str
    work_item_id: str
    employee_id: str
    role: str
    sandbox_id: str
    base_commit: str
    summary: str
    changed_files: list[str]
    diff_stat: str
    git_diff: str
    tests_requested: list[dict[str, Any]]
    tests_executed: list[dict[str, Any]]
    test_results: list[TestResult]
    started_at: str
    completed_at: str
    status: str  # "SUCCESS" | "FAILED"
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "work_item_id": self.work_item_id,
            "employee_id": self.employee_id,
            "role": self.role,
            "sandbox_id": self.sandbox_id,
            "base_commit": self.base_commit,
            "summary": self.summary,
            "changed_files": self.changed_files,
            "diff_stat": self.diff_stat,
            "git_diff": self.git_diff,
            "tests_requested": self.tests_requested,
            "tests_executed": self.tests_executed,
            "test_results": [t.to_dict() for t in self.test_results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "output": {
                "summary": self.summary,
                "changed_files": self.changed_files,
                "diff_stat": self.diff_stat,
                "git_diff": self.git_diff,
                "test_results": [t.to_dict() for t in self.test_results],
            },
            "provider_metadata": self.provider_metadata,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ReviewArtifact:
    """Canonical record of SENTRY QA technical evaluation over PatchArtifact and TestResults."""

    review_id: str
    work_item_id: str
    employee_id: str
    role: str
    reviewed_artifact_ids: list[str]
    decision: str  # "APPROVE_TECHNICAL" | "REQUEST_CHANGES"
    findings: list[str]
    risks: list[str]
    test_evidence_reviewed: dict[str, Any]
    recommended_action: str
    started_at: str
    completed_at: str
    status: str = "COMPLETED"
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def artifact_id(self) -> str:
        return self.review_id

    @property
    def summary(self) -> str:
        return f"Technical Review: {self.decision} ({len(self.findings)} findings)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "artifact_id": self.review_id,
            "work_item_id": self.work_item_id,
            "employee_id": self.employee_id,
            "role": self.role,
            "reviewed_artifact_ids": self.reviewed_artifact_ids,
            "decision": self.decision,
            "findings": self.findings,
            "risks": self.risks,
            "test_evidence_reviewed": self.test_evidence_reviewed,
            "recommended_action": self.recommended_action,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "summary": f"Technical Review: {self.decision} ({len(self.findings)} findings)",
            "output": {
                "decision": self.decision,
                "findings": self.findings,
                "risks": self.risks,
                "recommended_action": self.recommended_action,
                "test_evidence_reviewed": self.test_evidence_reviewed,
            },
            "provider_metadata": self.provider_metadata,
            "metadata": self.metadata,
        }


# ==============================================================================
# PATH & CHANGE POLICY VALIDATION
# ==============================================================================

ALLOWED_SUBTREES = (
    "CORE-SERVICES/",
    "AI5R-STUDIO/",
    "AI5R-SDK/",
    "PRODUCTS/",
)

DENIED_PATH_PATTERNS = [
    re.compile(r"(^|[/\\])\.git([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])\.env", re.IGNORECASE),
    re.compile(r"(credentials|secrets|private_key|id_rsa|id_ed25519)", re.IGNORECASE),
    re.compile(r"(^|[/\\])\.ssh([/\\]|$)", re.IGNORECASE),
    re.compile(r"(runtime[/\\]backups|backups)", re.IGNORECASE),
    re.compile(r"(production_config|compose\.yaml)", re.IGNORECASE),
]

FORBIDDEN_METATOKENS = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]


class PathSecurityError(ValueError):
    """Raised when a proposed path violates safety policies."""


class PathPolicyValidator:
    """Enforces strict path containment, traversal denial, symlink defense, and allowable subtrees."""

    @staticmethod
    def validate_change(sandbox_root: Path, change: dict[str, Any]) -> tuple[str, str, str]:
        if not isinstance(change, dict):
            raise PathSecurityError("Change proposal must be a JSON object")

        raw_path = change.get("path")
        operation = change.get("operation")
        content = change.get("content")

        if not raw_path or not isinstance(raw_path, str):
            raise PathSecurityError("Change requires a non-empty 'path' string")

        if operation not in ("create", "modify"):
            raise PathSecurityError(f"Unsupported operation '{operation}'. Only 'create' and 'modify' are allowed")

        if content is None or not isinstance(content, str):
            raise PathSecurityError("Change requires a text 'content' string")

        # Bounded content size: 1 MB
        if len(content.encode("utf-8")) > 1_048_576:
            raise PathSecurityError("Change content exceeds maximum allowed size of 1 MB")

        # Reject absolute paths (Windows & Unix) and UNC paths
        if raw_path.startswith("\\\\"):
            raise PathSecurityError(f"UNC path '{raw_path}' is denied")

        if os.path.isabs(raw_path) or raw_path.startswith(("/", "\\")):
            raise PathSecurityError(f"Absolute path '{raw_path}' is denied")

        if re.match(r"^[a-zA-Z]:", raw_path):
            raise PathSecurityError(f"Drive-letter path '{raw_path}' is denied")

        # Reject traversal tokens
        if ".." in raw_path or "../" in raw_path or "..\\" in raw_path:
            raise PathSecurityError(f"Path traversal '{raw_path}' is strictly denied")

        # Normalize relative path
        normalized = os.path.normpath(raw_path).replace("\\", "/")
        if normalized.startswith("../") or normalized == "..":
            raise PathSecurityError(f"Normalized traversal path '{raw_path}' is strictly denied")

        # Allowed subtrees check
        if not any(normalized.startswith(subtree) for subtree in ALLOWED_SUBTREES):
            raise PathSecurityError(
                f"Path '{normalized}' is not within allowed subtrees: {', '.join(ALLOWED_SUBTREES)}"
            )

        # Denied patterns
        for pattern in DENIED_PATH_PATTERNS:
            if pattern.search(normalized):
                raise PathSecurityError(f"Path '{normalized}' matches denied pattern '{pattern.pattern}'")

        # Symlink / Reparse point containment check
        resolved_sandbox_root = sandbox_root.resolve()
        target_path = (sandbox_root / normalized)

        # Walk up existing parents and verify none escape via symlink
        check_p = target_path
        while check_p != sandbox_root:
            if check_p.exists():
                resolved_p = check_p.resolve()
                try:
                    resolved_p.relative_to(resolved_sandbox_root)
                except ValueError as err:
                    raise PathSecurityError(
                        f"Symlink escape detected: '{normalized}' resolves outside sandbox root"
                    ) from err
                if check_p.is_symlink():
                    resolved_link = check_p.resolve()
                    try:
                        resolved_link.relative_to(resolved_sandbox_root)
                    except ValueError as err:
                        raise PathSecurityError(
                            f"Symlink escape detected: link '{check_p}' targets '{resolved_link}' outside sandbox"
                        ) from err
            check_p = check_p.parent

        return normalized, operation, content


# ==============================================================================
# ALLOWLISTED TEST RUNNER
# ==============================================================================

class TestRunnerPolicy:
    """Executes only predefined, allowlisted test targets with shell=False and bounded timeout."""

    @staticmethod
    def run_test(
        sandbox_root: Path,
        kind: str,
        target: str,
        timeout: float = 30.0,
    ) -> TestResult:
        # Validate target does not contain metacharacters or command chaining
        for token in FORBIDDEN_METATOKENS:
            if token in target:
                raise ValueError(f"Command metacharacter '{token}' denied in test target")

        norm_kind = kind.upper().strip()
        command_args: list[str]

        if norm_kind in ("PYTEST", "PYTEST_TARGET"):
            # Target must be safe path in CORE-SERVICES or tests
            if ".." in target or target.startswith(("/", "\\")):
                raise ValueError("Target path must be relative without traversal")
            command_args = [sys.executable, "-m", "pytest", "-q", target]

        elif norm_kind in ("VITEST", "VITEST_TARGET", "NPM_TEST_TARGET"):
            if ".." in target or target.startswith(("/", "\\")):
                raise ValueError("Target path must be relative without traversal")
            npx_bin = "npm.cmd" if sys.platform == "win32" else "npm"
            command_args = [npx_bin, "run", "test", "--", target, "--run"]

        elif norm_kind in ("LINT", "LINT_TARGET"):
            if ".." in target or target.startswith(("/", "\\")):
                raise ValueError("Target path must be relative without traversal")
            oxlint_bin = "npx.cmd" if sys.platform == "win32" else "npx"
            command_args = [oxlint_bin, "oxlint", target]

        else:
            raise ValueError(f"Unsupported test kind '{kind}'. Allowed kinds: PYTEST, VITEST, LINT")

        # Controlled environment: strip sensitive variables
        safe_env = {
            k: v
            for k, v in os.environ.items()
            if not any(secret in k.upper() for secret in ("KEY", "SECRET", "PASSWORD", "TOKEN", "AUTH"))
        }
        safe_env["PYTHONPATH"] = str(sandbox_root / "CORE-SERVICES") + os.pathsep + str(sandbox_root / "AI5R-SDK")

        start_time = time.perf_counter()
        test_id = f"TR-{uuid4().hex[:8].upper()}"

        try:
            cwd_path = str(sandbox_root)
            # In vitest/lint, run from dashboard if target is frontend
            if norm_kind in ("VITEST", "VITEST_TARGET", "NPM_TEST_TARGET", "LINT", "LINT_TARGET"):
                dashboard_dir = sandbox_root / "AI5R-STUDIO" / "dashboard"
                if dashboard_dir.exists():
                    cwd_path = str(dashboard_dir)

            proc = subprocess.run(
                command_args,
                cwd=cwd_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                env=safe_env,
            )
            duration = time.perf_counter() - start_time
            return TestResult(
                test_result_id=test_id,
                command_id=norm_kind,
                target=target,
                exit_code=proc.returncode,
                passed=(proc.returncode == 0),
                duration=round(duration, 3),
                stdout_summary=proc.stdout[:4000],
                stderr_summary=proc.stderr[:4000],
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start_time
            return TestResult(
                test_result_id=test_id,
                command_id=norm_kind,
                target=target,
                exit_code=124,
                passed=False,
                duration=round(duration, 3),
                stdout_summary=str(exc.stdout or "")[:2000],
                stderr_summary="Execution timed out",
                timed_out=True,
            )
        except Exception as exc:
            duration = time.perf_counter() - start_time
            return TestResult(
                test_result_id=test_id,
                command_id=norm_kind,
                target=target,
                exit_code=1,
                passed=False,
                duration=round(duration, 3),
                stdout_summary="",
                stderr_summary=f"Execution error: {exc}",
                timed_out=False,
            )


# ==============================================================================
# CODING SANDBOX
# ==============================================================================

class CodingSandbox:
    """Isolated, disposable git worktree sandbox created outside product repositories."""

    def __init__(
        self,
        sandbox_id: str,
        work_item_id: str,
        employee_id: str,
        base_commit: str,
        root_path: Path,
        repo_dir: Path,
    ) -> None:
        self.sandbox_id = sandbox_id
        self.work_item_id = work_item_id
        self.employee_id = employee_id
        self.base_commit = base_commit
        self.root_path = root_path
        self.repo_dir = repo_dir
        self.created_at = _now()
        self.status = "ACTIVE"
        self._changed_files: list[str] = []

    def apply_changes(self, changes: list[dict[str, Any]]) -> list[str]:
        """Validate and apply structured file modifications inside this sandbox."""
        if self.status != "ACTIVE":
            raise RuntimeError(f"Cannot apply changes: sandbox is in status '{self.status}'")

        applied: list[str] = []
        for change in changes:
            rel_path, operation, content = PathPolicyValidator.validate_change(self.root_path, change)
            full_path = self.root_path / rel_path

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file deterministically
            full_path.write_text(content, encoding="utf-8")
            applied.append(rel_path)

        self._changed_files = list(dict.fromkeys(self._changed_files + applied))
        return applied

    def generate_diff(self) -> tuple[list[str], str, str]:
        """Capture real git diff and status from the sandbox worktree."""
        if not self.root_path.exists():
            return [], "", ""

        # Include untracked files in git diff
        subprocess.run(
            ["git", "add", "-N", "."],
            cwd=str(self.root_path),
            capture_output=True,
            shell=False,
        )

        stat_proc = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=str(self.root_path),
            capture_output=True,
            text=True,
            shell=False,
        )
        diff_stat = stat_proc.stdout.strip()

        diff_proc = subprocess.run(
            ["git", "diff"],
            cwd=str(self.root_path),
            capture_output=True,
            text=True,
            shell=False,
        )
        git_diff = diff_proc.stdout

        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(self.root_path),
            capture_output=True,
            text=True,
            shell=False,
        )
        changed = []
        for line in status_proc.stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    changed.append(parts[1].replace("\\", "/"))

        # Bound diff display to 64 KB
        if len(git_diff.encode("utf-8")) > 65_536:
            git_diff = git_diff[:65_000] + "\n\n[DIFF TRUNCATED: DISPLAY EXCEEDS 64KB LIMIT]"

        return changed, diff_stat, git_diff

    def run_tests(self, requested_tests: list[dict[str, Any]]) -> list[TestResult]:
        """Execute allowlisted tests inside the sandbox workspace."""
        results: list[TestResult] = []
        for test_req in requested_tests:
            kind = test_req.get("kind", "PYTEST")
            target = test_req.get("target", "")
            if not target:
                continue
            res = TestRunnerPolicy.run_test(self.root_path, kind=kind, target=target)
            results.append(res)
        return results

    def cleanup(self) -> None:
        """Safely delete the isolated git worktree and directory."""
        if self.status == "CLEANED":
            return

        resolved_root = str(self.root_path.resolve()).lower()
        repo_resolved = str(self.repo_dir.resolve()).lower()

        # Hard guard: never clean up product repositories
        if "ai5r-ai-employees" in resolved_root and resolved_root == repo_resolved:
            raise RuntimeError("Refusing cleanup: root matches product repository root")
        if "ai5r-current" in resolved_root:
            raise RuntimeError("Refusing cleanup: root points to AI5R-CURRENT")

        # Remove git worktree registration
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(self.root_path)],
            cwd=str(self.repo_dir),
            capture_output=True,
            shell=False,
        )

        # Clean filesystem directory if it remains
        if self.root_path.exists():
            shutil.rmtree(self.root_path, ignore_errors=True)

        self.status = "CLEANED"


# ==============================================================================
# SANDBOX MANAGER
# ==============================================================================

class SandboxManager:
    """Manages creation, registry, and lifecycle of CodingSandbox workspaces."""

    def __init__(self, repo_dir: Path | None = None, base_parent: Path | None = None) -> None:
        self.repo_dir = (repo_dir or Path.cwd()).resolve()
        self.base_parent = (base_parent or (Path(tempfile.gettempdir()) / "ai5r_sandboxes")).resolve()
        self.base_parent.mkdir(parents=True, exist_ok=True)
        self._sandboxes: dict[str, CodingSandbox] = {}

    def get_current_base_commit(self) -> str:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
            shell=False,
            check=True,
        )
        return proc.stdout.strip()

    def create_sandbox(
        self,
        work_item_id: str,
        employee_id: str,
        base_commit: str | None = None,
    ) -> CodingSandbox:
        commit = base_commit or self.get_current_base_commit()
        sandbox_id = f"SBX-{uuid4().hex[:12].upper()}"
        sandbox_root = self.base_parent / sandbox_id

        # Hard guard against creating inside product repos
        resolved_new = str(sandbox_root.resolve()).lower()
        if "ai5r-ai-employees" in resolved_new and resolved_new == str(self.repo_dir.resolve()).lower():
            raise RuntimeError("Sandbox root cannot be the source worktree")
        if "ai5r-current" in resolved_new:
            raise RuntimeError("Sandbox root cannot be AI5R-CURRENT")

        # Create detached git worktree
        proc = subprocess.run(
            ["git", "worktree", "add", "--detach", str(sandbox_root), commit],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
            shell=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to create git worktree sandbox: {proc.stderr}")

        sandbox = CodingSandbox(
            sandbox_id=sandbox_id,
            work_item_id=work_item_id,
            employee_id=employee_id,
            base_commit=commit,
            root_path=sandbox_root,
            repo_dir=self.repo_dir,
        )
        self._sandboxes[sandbox_id] = sandbox
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> CodingSandbox | None:
        return self._sandboxes.get(sandbox_id)

    def cleanup_sandbox(self, sandbox_id: str) -> None:
        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox:
            sandbox.cleanup()
