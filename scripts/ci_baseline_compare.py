#!/usr/bin/env python3
"""Baseline regression reporter for the AI5R IT Agent Foundation CI.

Stdlib only. Reads plain-text output artifacts the raw test jobs already
produce and diffs the failing test IDs/files against a committed baseline
manifest. This script never runs a test itself and never changes any raw
job's exit status -- it only classifies what those jobs already reported.

Deliberately does NOT reconstruct pytest node IDs from JUnit XML
classnames (that mapping depends on rootdir/invocation details not yet
empirically observed from a real run in this repo, and getting it wrong
silently would be exactly the "fragile parser" this design avoids).
Instead it greps pytest's own "-q" short-summary lines
("FAILED <nodeid> - ..." / "ERROR <nodeid> - ...") -- the literal,
already-correct node ID format pytest itself prints, the same format the
baseline manifest below was hand-built from by reading a real CI run
(https://github.com/alfikrraid-cmd/AI5R/actions/runs/33256494001). No
regex-based scraping of colorized/stack-trace output is used for
matching -- only these two fixed, documented pytest summary-line
prefixes.

Three outcomes per suite:
  KNOWN_BASELINE_FAILURE     -- failing now, was already failing at
                                baseline capture time. Legacy debt.
  NEW_FAILURE                -- failing now, was NOT in the baseline.
                                This is the actual regression signal.
  RESOLVED_BASELINE_FAILURE  -- was in the baseline, not failing now.
                                Good news -- the baseline manifest should
                                be updated in a follow-up change, not
                                silently left stale (this script only
                                reports it, never edits the manifest).

Exit code: 0 unless at least one NEW_FAILURE was found -- this job
answers "did this branch regress," not "are all tests green." The raw
pytest/vitest jobs already report their own real exit status separately
and are never touched by this script.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "ENGINEERING" / "IT-AGENT" / "CI-BASELINE" / "known-failures.json"
ARTIFACTS_DIR = REPO_ROOT / "ci-artifacts"

# Matches pytest's own "-q" short test summary info lines, e.g.:
#   FAILED TESTS/test_import_router.py::test_foo - AssertionError: ...
#   ERROR TESTS/test_import_router.py::test_bar - subprocess.CalledProcessError: ...
PYTEST_SUMMARY_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)\s+-\s")


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        print(f"ERROR: baseline manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def pytest_failed_ids(output_path: Path) -> set[str]:
    """Extract node IDs from pytest's own '-q' short summary lines.
    Returns an empty set (not an error) if the artifact is genuinely
    absent -- a job that never produced output should not fabricate
    failures."""
    if not output_path.is_file():
        print(f"NOTE: {output_path} not found -- treating as no data for this suite.")
        return set()
    ids: set[str] = set()
    for line in output_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PYTEST_SUMMARY_RE.match(line.strip())
        if m:
            ids.add(m.group(1))
    return ids


def vitest_failed_files(json_path: Path) -> set[str]:
    """vitest's --reporter=json output is a documented, stable structured
    format (testResults[].name / .status) -- safe to parse directly,
    unlike scraping colorized terminal output."""
    if not json_path.is_file():
        print(f"NOTE: {json_path} not found -- treating as no data for this suite.")
        return set()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    failed = set()
    for result in data.get("testResults", []):
        if result.get("status") == "failed" or result.get("numFailingTests", 0) > 0:
            name = result.get("name", "")
            if "src/" in name:
                name = "src/" + name.split("src/", 1)[1]
            failed.add(name)
    return failed


def report(label: str, known: set[str], observed_failing: set[str]) -> bool:
    """Print the 3-way classification for one suite. Return True if any
    NEW_FAILURE was found."""
    new = sorted(observed_failing - known)
    known_and_failing = sorted(observed_failing & known)
    resolved = sorted(known - observed_failing)

    print(f"\n=== {label} ===")
    print(f"KNOWN_BASELINE_FAILURE ({len(known_and_failing)}):")
    for t in known_and_failing:
        print(f"  - {t}")
    print(f"NEW_FAILURE ({len(new)}):")
    for t in new:
        print(f"  - {t}")
    print(f"RESOLVED_BASELINE_FAILURE ({len(resolved)}):")
    for t in resolved:
        print(f"  - {t}")

    return len(new) > 0


def main() -> int:
    manifest = load_manifest()
    regression = False

    backend_known = set(manifest.get("backend_dependency_blocked", [])) | set(
        manifest.get("backend_real_stack_integration", [])
    )
    backend_failing = pytest_failed_ids(ARTIFACTS_DIR / "backend-api-tests" / "pytest-output.txt")
    regression |= report("BACKEND-API/TESTS", backend_known, backend_failing)

    # CORE-SERVICES/API/TESTS has never run in CI before this workflow
    # revision -- there is no baseline to diff against yet. Report its
    # raw failing IDs as observational data only (never as NEW_FAILURE),
    # so this first run isn't mislabeled as a regression it isn't.
    core_services_failing = pytest_failed_ids(
        ARTIFACTS_DIR / "core-services-api-tests" / "pytest-output.txt"
    )
    print("\n=== CORE-SERVICES/API/TESTS ===")
    print("No baseline exists yet for this suite (first CI execution under this workflow).")
    print(f"Observed failing ({len(core_services_failing)}), for future baseline-capture only:")
    for t in sorted(core_services_failing):
        print(f"  - {t}")

    frontend_known = set(manifest.get("frontend_known_failing_files", []))
    frontend_failing = vitest_failed_files(
        ARTIFACTS_DIR / "frontend-tests" / "frontend-test-results.json"
    )
    regression |= report("FRONTEND TESTS", frontend_known, frontend_failing)

    if regression:
        print("\nREGRESSION DETECTED: at least one NEW_FAILURE not present in the baseline manifest.")
        return 1

    print("\nNo new regressions vs the committed baseline. Legacy/known failures (if any) are listed above, unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
