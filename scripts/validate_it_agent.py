#!/usr/bin/env python3
"""Structural validator for the AI5R IT Agent Foundation. Stdlib only —
no third-party dependency. Exits non-zero on any failure so CI can gate
on it. Read-only: never modifies repo files.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = REPO_ROOT / ".claude"
IT_AGENT_DIR = REPO_ROOT / "ENGINEERING" / "IT-AGENT"

REQUIRED_NATIVE_SKILLS = ["ai5r-it-orchestrator", "ai5r-observability"]

# Must match the orchestrator's own "Role -> specialist map" table.
EXPECTED_AGENTS = [
    "planner", "architect", "code-architect", "fastapi-reviewer",
    "python-reviewer", "react-reviewer", "database-reviewer",
    "code-reviewer", "silent-failure-hunter", "security-reviewer",
    "network-troubleshooter", "doc-updater", "tdd-guide",
]
EXPECTED_SKILLS = [
    "fastapi-patterns", "python-patterns", "backend-patterns",
    "postgres-patterns", "react-patterns", "react-testing",
    "tdd-workflow", "python-testing", "docker-patterns",
    "security-review", "architecture-decision-records",
    "hexagonal-architecture", "living-docs-governance",
]

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def check_frontmatter(path: Path) -> None:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(REPO_ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        fail(f"no YAML frontmatter block: {path.relative_to(REPO_ROOT)}")
        return
    fm = m.group(1)
    if "name:" not in fm:
        fail(f"frontmatter missing 'name:': {path.relative_to(REPO_ROOT)}")
    if "description:" not in fm:
        fail(f"frontmatter missing 'description:': {path.relative_to(REPO_ROOT)}")


def main() -> int:
    # 1. Agent frontmatter
    for name in EXPECTED_AGENTS:
        check_frontmatter(CLAUDE_DIR / "agents" / f"{name}.md")

    # 2. Vendored skill frontmatter
    for name in EXPECTED_SKILLS:
        check_frontmatter(CLAUDE_DIR / "skills" / name / "SKILL.md")

    # 3. Required AI5R-native skills exist, with origin: AI5R
    for name in REQUIRED_NATIVE_SKILLS:
        path = CLAUDE_DIR / "skills" / name / "SKILL.md"
        check_frontmatter(path)
        if path.is_file() and "origin: AI5R" not in path.read_text(encoding="utf-8"):
            fail(f"native skill missing 'origin: AI5R' in frontmatter: {path.relative_to(REPO_ROOT)}")

    # 4. Orchestrator specialist references resolve to real files
    orchestrator = CLAUDE_DIR / "skills" / "ai5r-it-orchestrator" / "SKILL.md"
    if orchestrator.is_file():
        text = orchestrator.read_text(encoding="utf-8")
        for name in EXPECTED_AGENTS:
            if f"`{name}`" not in text:
                fail(f"orchestrator role map does not reference agent '{name}'")
        for name in EXPECTED_SKILLS:
            if f"`{name}`" not in text:
                fail(f"orchestrator role map does not reference skill '{name}'")
        for name in REQUIRED_NATIVE_SKILLS:
            if name not in text:
                fail(f"orchestrator does not reference native skill '{name}'")
    else:
        fail("ai5r-it-orchestrator/SKILL.md missing — cannot check role map")

    # 5. Max-specialist dispatch policy present
    if orchestrator.is_file():
        text = orchestrator.read_text(encoding="utf-8")
        if not re.search(r"Maximum:\s*2", text):
            fail("dispatch policy 'Maximum: 2' not found in ai5r-it-orchestrator/SKILL.md")
        if "Default: 1 specialist" not in text:
            fail("dispatch policy 'Default: 1 specialist' not found in ai5r-it-orchestrator/SKILL.md")

    # 6. Shared-host safety policy present (added Phase 2.6)
    if orchestrator.is_file():
        text = orchestrator.read_text(encoding="utf-8")
        if "Shared-host safety" not in text:
            fail("'Shared-host safety' section missing from ai5r-it-orchestrator/SKILL.md")

    # 7. ECC attribution + pinned commit exist
    attribution = IT_AGENT_DIR / "ECC-ATTRIBUTION.md"
    if not attribution.is_file():
        fail(f"missing file: {attribution.relative_to(REPO_ROOT)}")
    else:
        text = attribution.read_text(encoding="utf-8")
        m = re.search(r"Pinned commit:\s*`([0-9a-f]{40})`", text)
        if not m:
            fail("ECC-ATTRIBUTION.md missing a 'Pinned commit: `<40-hex-char-sha>`' line")

    # 8. Explicitly-not-vendored list still documented (no silent full-plugin adoption)
    if attribution.is_file():
        text = attribution.read_text(encoding="utf-8")
        for name in ("chief-of-staff", "build-error-resolver", "unified-memory", "security-scan"):
            if name not in text:
                fail(f"ECC-ATTRIBUTION.md missing rejection record for '{name}'")

    if failures:
        print(f"\n{len(failures)} check(s) failed.")
        return 1

    print("All IT Agent Foundation structural checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
