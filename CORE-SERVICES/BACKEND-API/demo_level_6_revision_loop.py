import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.extend([
    str(REPO_ROOT),
    str(REPO_ROOT / "CORE-SERVICES"),
    str(REPO_ROOT / "CORE-SERVICES" / "BACKEND-API"),
    str(REPO_ROOT / "AI5R-SDK"),
])

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from API.coding_sandbox import SandboxManager
from API.execution_ledger import ExecutionLedger
from API.workforce_service import WorkforceService
from API.mission_lifecycle import MissionStatus
from TESTS.test_level_6_revision_loop import ConfigurableRoleAI


def run_level_6_e2e_demo():
    print("=" * 80)
    print("AI5R WORKFORCE LEVEL 6 -- BOUNDED AUTONOMOUS REVISION LOOP DEMONSTRATION")
    print("=" * 80)

    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        ledger_path = Path(tmp_dir) / "demo_level_6_ledger.db"
        ledger = ExecutionLedger(ledger_path)
        service = WorkforceService(organization_name="AI5R Autonomous Engineering", ledger=ledger)
        service.execution_adapter.sandbox_manager = SandboxManager(repo_dir=REPO_ROOT)

        # ----------------------------------------------------------------------
        # STEP 1: CHIEF SUBMITS MISSION
        # ----------------------------------------------------------------------
        print("\n[STEP 1] Chief submits mission...")
        mission_input = {
            "title": "Fix CM History pagination so all historical CM readings can be accessed without losing occurrence isolation",
            "description": "Ensure occurrence-isolated CM readings display correctly across multi-page queries without duplicate entries.",
            "is_production": True,
            "include_security": True,
            "max_iterations": 3,
        }
        mission = service.create_mission(
            title=mission_input["title"],
            description=mission_input["description"],
            is_production=mission_input["is_production"],
            include_security=mission_input["include_security"],
            max_iterations=mission_input["max_iterations"],
        )
        mission_id = mission["mission_id"]
        print(f"  ✓ Mission Created: {mission_id}")
        print(f"  ✓ Title: {mission['title']}")
        print(f"  ✓ Status: {mission['status']}")
        print(f"  ✓ Governance: is_production={mission['is_production']}, max_iterations={mission['max_iterations']}")

        # ----------------------------------------------------------------------
        # STEP 2: NEXA GENERATES PLAN & TASK DECOMPOSITION
        # ----------------------------------------------------------------------
        print("\n[STEP 2] NEXA generates execution plan & task decomposition...")
        mission_details = service.get_mission(mission_id)
        plan = mission_details.get("execution_plan", {})
        tasks = mission_details.get("tasks", [])
        print(f"  ✓ Plan ID: {mission_details.get('plan_id')}")
        print(f"  ✓ Decomposed Tasks: {len(tasks)}")
        for t in tasks:
            deps = t.get("dependencies", [])
            dep_str = f"depends on {deps}" if deps else "Root task"
            print(f"    - [{t['assigned_position_id']}] {t['title']} ({dep_str})")

        # ----------------------------------------------------------------------
        # STEP 3: CONFIGURE SPECIALIST AI FOR REVISION DEMONSTRATION
        # ----------------------------------------------------------------------
        print("\n[STEP 3] Initializing Specialist AI & Sentry Reviewers...")
        mock_ai = ConfigurableRoleAI(
            qa_decisions=[
                # Attempt 0: QA fails due to duplicated pagination items
                {
                    "decision": "REQUEST_CHANGES",
                    "summary": "Detected row duplication on page 2",
                    "findings": ["Show More duplicates rows after page 2"],
                    "risks": ["Data duplication on UI and occurrence leakage"],
                    "recommended_action": "Deduplicate appended items by occurrence ID in frontend state",
                },
                # Attempt 1 (Re-review): QA passes
                {
                    "decision": "APPROVE_TECHNICAL",
                    "summary": "Pagination deduplication verified successfully; no occurrence leakage",
                    "findings": [],
                    "risks": [],
                },
            ],
            security_decisions=[
                # Security review passes cleanly
                {
                    "decision": "APPROVE_TECHNICAL",
                    "summary": "Security audit verified: access control and occurrence isolation verified",
                    "findings": [],
                    "risks": [],
                }
            ],
            code_patches=[
                # Initial patch (contains bug)
                {
                    "summary": "Initial frontend pagination logic",
                    "changes": [
                        {
                            "path": "AI5R-STUDIO/dashboard/src/modules/workforce/cm_history.js",
                            "operation": "create",
                            "content": "export function appendRows(existing, next) { return existing.concat(next); }\n",
                        }
                    ],
                    "requested_tests": [],
                },
                # Revision patch (fixes bug by deduplicating)
                {
                    "summary": "Fixed deduplication by occurrence ID",
                    "changes": [
                        {
                            "path": "AI5R-STUDIO/dashboard/src/modules/workforce/cm_history.js",
                            "operation": "modify",
                            "content": "export function appendRows(existing, next) { const ids = new Set(existing.map(r => r.id)); return existing.concat(next.filter(r => !ids.has(r.id))); }\n",
                        }
                    ],
                    "requested_tests": [],
                },
            ],
        )

        # ----------------------------------------------------------------------
        # STEP 4 TO 10: RUN GOVERNED AUTONOMOUS EXECUTION LOOP
        # ----------------------------------------------------------------------
        print("\n[STEP 4-10] Starting Level 6 Governed Autonomous Revision Loop...")
        result = service.orchestrate_mission(
            mission_id=mission_id,
            ai_client=mock_ai,
            sentry_client=mock_ai,
            security_client=mock_ai,
        )

        print(f"  ✓ Autonomous Execution Status: {result['status']}")
        print(f"  ✓ Revision Iteration: {result['current_iteration']} / {result['max_iterations']}")
        print(f"  ✓ QA Review Decision: {result['latest_review_result']['decision']}")
        print(f"  ✓ Security Review Decision: {result['latest_security_review_result']['decision']}")
        print(f"  ✓ Chief Approval Status: {result['approval_status']}")

        findings = service.get_mission_findings(mission_id)
        print(f"\n[STEP 5-6] Structured Review Findings Logged ({len(findings)}):")
        for f in findings:
            print(f"  - [{f['severity']}] {f['finding_id']}: {f['description']}")
            print(f"    Category: {f['category']} | Role: {f['responsible_role']} | Action: {f['required_action']}")
            print(f"    Status: {f['status']}")

        # ----------------------------------------------------------------------
        # STEP 11: HUMAN CHIEF EXPLICIT APPROVAL
        # ----------------------------------------------------------------------
        print("\n[STEP 11] Human Chief Approval Gate reached. Dispatching explicit Chief approval...")
        approved_result = service.approve_mission(
            mission_id=mission_id,
            approver_id="raid",
            approver_role="CHIEF_ARCHITECT",
            is_human=True,
        )
        print(f"  ✓ Chief Approval Granted by: raid (CHIEF_ARCHITECT)")
        print(f"  ✓ Final Mission Status: {approved_result['status']}")
        print(f"  ✓ Final Approval Status: {approved_result['approval_status']}")

        # ----------------------------------------------------------------------
        # STEP 12: EXECUTION LEDGER AUDIT TRAIL
        # ----------------------------------------------------------------------
        print("\n[STEP 12] Inspecting Immutable Execution Ledger...")
        events = service.get_mission_events(mission_id)
        print(f"  ✓ Total Audit Events Recorded: {len(events)}")
        print("  ✓ Ordered Event Trail:")
        for idx, evt in enumerate(events, 1):
            actor = f"{evt['role']} ({evt['who']})" if evt.get("who") else evt.get("role", "SYSTEM")
            print(f"    {idx:02d}. [{evt['event_type']}] by {actor} -> {evt['result'] or 'OK'} | {evt['what']}")

        print("\n" + "=" * 80)
        print("DEMONSTRATION RESULT: LEVEL 6 BOUNDED AUTONOMOUS REVISION LOOP VERIFIED")
        print("=" * 80)


if __name__ == "__main__":
    run_level_6_e2e_demo()
