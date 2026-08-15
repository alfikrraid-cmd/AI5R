from __future__ import annotations

import ast
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = "CORE-SERVICES/BACKEND-API/main.py"
LOCAL_ROOTS = (
    "CORE-SERVICES/BACKEND-API",
    "CORE-SERVICES",
    "AI5R-SDK",
    "PRODUCTS/LTSA-BRAIN/INGESTION",
)
LOCAL_TOP_LEVELS = {"routers", "API", "models", "dependencies"}


def git_lines(*args: str) -> list[str]:
    output = subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True)
    return [line for line in output.splitlines() if line]


def git_show(path: str) -> str:
    return subprocess.check_output(["git", "show", f":{path}"], cwd=REPO_ROOT, text=True)


def tracked_files() -> set[str]:
    return set(git_lines("ls-files", "--cached"))


def docker_context_roots() -> set[str]:
    dockerfile = REPO_ROOT / "CORE-SERVICES/RUNTIME/docker/api.Dockerfile"
    roots: set[str] = set()

    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("COPY "):
            continue

        parts = line.split()
        if len(parts) >= 3 and not parts[1].startswith("--"):
            roots.add(parts[1].rstrip("/"))

    return roots


def candidates(module: str) -> list[str]:
    parts = module.split(".") if module else []
    results: list[str] = []

    for root in LOCAL_ROOTS:
        base = "/".join((root, *parts))
        results.append(f"{base}.py")
        results.append(f"{base}/__init__.py")

    return results


def resolve_absolute(module: str, tracked: set[str]) -> str | None:
    for candidate in candidates(module):
        if candidate in tracked:
            return candidate
    return None


def resolve_relative(current: str, level: int, module: str | None, tracked: set[str]) -> str | None:
    directory = Path(current).parent
    for _ in range(level - 1):
        directory = directory.parent

    parts = module.split(".") if module else []
    base = directory.joinpath(*parts).as_posix()

    for candidate in (f"{base}.py", f"{base}/__init__.py"):
        if candidate in tracked:
            return candidate
    return None


def is_local_module(module: str | None, tracked: set[str]) -> bool:
    if not module:
        return False
    return module.split(".")[0] in LOCAL_TOP_LEVELS or resolve_absolute(module, tracked) is not None


def imported_local_files(current: str, tracked: set[str]) -> tuple[list[str], list[str]]:
    tree = ast.parse(git_show(current), filename=current)
    resolved: list[str] = []
    issues: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not is_local_module(alias.name, tracked):
                    continue
                target = resolve_absolute(alias.name, tracked)
                if target is None:
                    issues.append(f"{current}: unresolved import {alias.name}")
                else:
                    resolved.append(target)

        if isinstance(node, ast.ImportFrom):
            if node.level:
                target = resolve_relative(current, node.level, node.module, tracked)
                if target is not None:
                    resolved.append(target)
                elif node.module:
                    issues.append(f"{current}: unresolved relative import {'.' * node.level}{node.module}")

                for alias in node.names:
                    nested = ".".join(part for part in (node.module, alias.name) if part)
                    target = resolve_relative(current, node.level, nested, tracked)
                    if target is not None:
                        resolved.append(target)
                continue

            if not is_local_module(node.module, tracked):
                continue

            target = resolve_absolute(node.module, tracked)
            if target is None:
                issues.append(f"{current}: unresolved import {node.module}")
            else:
                resolved.append(target)

            for alias in node.names:
                target = resolve_absolute(f"{node.module}.{alias.name}", tracked)
                if target is not None:
                    resolved.append(target)

    return resolved, issues


def test_production_api_entrypoint_import_graph_is_tracked_and_in_docker_context() -> None:
    tracked = tracked_files()
    docker_roots = docker_context_roots()
    visited: set[str] = set()
    pending = [ENTRYPOINT]
    issues: list[str] = []

    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)

        if current not in tracked:
            issues.append(f"{current}: not tracked by Git")

        disk_path = REPO_ROOT / current
        if not disk_path.is_file():
            issues.append(f"{current}: missing from working tree")
        elif disk_path.relative_to(REPO_ROOT).as_posix() != current:
            issues.append(f"{current}: path case mismatch")

        if not any(current == root or current.startswith(f"{root}/") for root in docker_roots):
            issues.append(f"{current}: not copied by production api.Dockerfile")

        resolved, import_issues = imported_local_files(current, tracked)
        issues.extend(import_issues)
        pending.extend(resolved)

    assert not issues
