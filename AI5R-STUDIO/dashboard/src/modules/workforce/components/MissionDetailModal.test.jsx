import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MissionDetailModal from "./MissionDetailModal";
import * as workforceClient from "../../../api/workforceClient";

vi.mock("../../../api/workforceClient", () => ({
  orchestrateWorkforceMission: vi.fn(),
  fetchMissionFindings: vi.fn(),
  fetchMissionEvents: vi.fn(),
  approveWorkforceMission: vi.fn(),
  rejectWorkforceMission: vi.fn(),
}));

describe("MissionDetailModal Level 6 UI", () => {
  const mockLevel6Mission = {
    mission_id: "MISSION-L6-TEST-001",
    title: "Fix CM History Pagination and Occurrence Isolation",
    description: "Ensure historical CM readings can be accessed without cross-occurrence leakage",
    is_production: true,
    status: "READY_FOR_CHIEF_APPROVAL",
    progress: 85,
    current_iteration: 1,
    max_iterations: 3,
    approval_status: "PENDING",
    created_by: "CHIEF",
    latest_review_result: {
      decision: "APPROVE_TECHNICAL",
      summary: "QA suite passed after revision 1",
    },
    latest_security_review_result: {
      decision: "APPROVE_TECHNICAL",
      summary: "Security audit passed with no vulnerabilities",
    },
    findings: [
      {
        finding_id: "FINDING-QA-001",
        severity: "HIGH",
        category: "CORRECTNESS",
        description: "Show More duplicates rows after page 2",
        affected_task_id: "TASK-FE-01",
        responsible_role: "FRONTEND_ENGINEER",
        required_action: "Deduplicate appended page items by occurrence ID",
        status: "RESOLVED",
      },
    ],
    tasks: [
      {
        work_item_id: "TASK-SA-01",
        title: "Inspect data flow",
        assigned_position_id: "SOLUTION_ARCHITECT",
        status: "COMPLETED",
        dependencies: [],
      },
      {
        work_item_id: "TASK-BE-01",
        title: "Verify API pagination",
        assigned_position_id: "BACKEND_ENGINEER",
        status: "COMPLETED",
        dependencies: ["TASK-SA-01"],
      },
      {
        work_item_id: "TASK-FE-01",
        title: "Fix UI pagination",
        assigned_position_id: "FRONTEND_ENGINEER",
        status: "COMPLETED",
        dependencies: ["TASK-SA-01"],
      },
      {
        work_item_id: "TASK-QA-01",
        title: "Execute automated QA suite",
        assigned_position_id: "QA_ENGINEER",
        status: "COMPLETED",
        dependencies: ["TASK-BE-01", "TASK-FE-01"],
      },
      {
        work_item_id: "TASK-SEC-01",
        title: "Verify security controls",
        assigned_position_id: "SECURITY_ENGINEER",
        status: "COMPLETED",
        dependencies: ["TASK-QA-01"],
      },
    ],
    execution_plan: {
      running: [],
      waiting: [],
      blocked: [],
      completed: ["TASK-SA-01", "TASK-BE-01", "TASK-FE-01", "TASK-QA-01", "TASK-SEC-01"],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    workforceClient.fetchMissionFindings.mockResolvedValue({
      findings: mockLevel6Mission.findings,
    });
    workforceClient.fetchMissionEvents.mockResolvedValue({
      events: [
        {
          event_id: "EVT-001",
          event_type: "MISSION_CREATED",
          actor_role: "CHIEF_ARCHITECT",
          task_id: null,
          timestamp: "2026-09-30T10:00:00Z",
        },
        {
          event_id: "EVT-002",
          event_type: "REVIEW_FAILED",
          actor_role: "QA_ENGINEER",
          task_id: "TASK-QA-01",
          timestamp: "2026-09-30T10:15:00Z",
        },
        {
          event_id: "EVT-003",
          event_type: "REVISION_REQUESTED",
          actor_role: "QA_ENGINEER",
          task_id: "TASK-FE-01",
          timestamp: "2026-09-30T10:16:00Z",
        },
        {
          event_id: "EVT-004",
          event_type: "REVIEW_PASSED",
          actor_role: "QA_ENGINEER",
          task_id: "TASK-QA-01",
          timestamp: "2026-09-30T10:30:00Z",
        },
      ],
    });
  });

  it("1. Renders Level 6 status bar with revision iteration counter, QA, Security, and Chief Gate status", () => {
    render(<MissionDetailModal isOpen={true} onClose={vi.fn()} mission={mockLevel6Mission} />);

    expect(screen.getByTestId("mission-level6-status")).toBeDefined();
    expect(screen.getByTestId("mission-revision-counter").textContent).toContain("Iteration 1 / 3");
    expect(screen.getByTestId("mission-qa-status").textContent).toContain("PASS");
    expect(screen.getByTestId("mission-security-status").textContent).toContain("PASS");
    expect(screen.getByTestId("mission-chief-approval-status").textContent).toContain("PENDING");
  });

  it("2. Switches tab to Autonomous Pipeline Flow and renders all lifecycle stages", () => {
    render(<MissionDetailModal isOpen={true} onClose={vi.fn()} mission={mockLevel6Mission} />);

    const flowTabBtn = screen.getByText("Autonomous Pipeline Flow");
    fireEvent.click(flowTabBtn);

    expect(screen.getByTestId("mission-pipeline-flow")).toBeDefined();
    expect(screen.getByText("1. Chief Mission Input")).toBeDefined();
    expect(screen.getByText("2. NEXA Task Decomposition & DAG")).toBeDefined();
    expect(screen.getByText("4. QA Verification")).toBeDefined();
    expect(screen.getByText("5. Security Review")).toBeDefined();
    expect(screen.getByText("6. Human Chief Approval Gate")).toBeDefined();
  });

  it("3. Switches tab to Review Findings and renders structured finding details", async () => {
    render(<MissionDetailModal isOpen={true} onClose={vi.fn()} mission={mockLevel6Mission} />);

    const findingsTabBtn = screen.getByText(/Review Findings/);
    fireEvent.click(findingsTabBtn);

    expect(screen.getByTestId("mission-findings-list")).toBeDefined();
    expect(screen.getByText(/Show More duplicates rows after page 2/)).toBeDefined();
    expect(screen.getByText(/Deduplicate appended page items by occurrence ID/)).toBeDefined();
    expect(screen.getByText("RESOLVED")).toBeDefined();
  });

  it("4. Switches tab to Execution Ledger and renders immutable ledger events", async () => {
    render(<MissionDetailModal isOpen={true} onClose={vi.fn()} mission={mockLevel6Mission} />);

    const eventsTabBtn = screen.getByText(/Execution Ledger/);
    fireEvent.click(eventsTabBtn);

    await waitFor(() => {
      expect(screen.getByTestId("mission-events-list")).toBeDefined();
      expect(screen.getByTestId("ledger-event-MISSION_CREATED")).toBeDefined();
      expect(screen.getByTestId("ledger-event-REVIEW_FAILED")).toBeDefined();
      expect(screen.getByTestId("ledger-event-REVISION_REQUESTED")).toBeDefined();
      expect(screen.getByTestId("ledger-event-REVIEW_PASSED")).toBeDefined();
    });
  });

  it("5. Displays Chief Gate controls when READY_FOR_CHIEF_APPROVAL and dispatches approve action", async () => {
    workforceClient.approveWorkforceMission.mockResolvedValue({
      mission: {
        ...mockLevel6Mission,
        status: "APPROVED",
        approval_status: "APPROVED",
      },
    });

    render(<MissionDetailModal isOpen={true} onClose={vi.fn()} mission={mockLevel6Mission} />);

    const approveBtn = screen.getByTestId("chief-approve-btn");
    expect(approveBtn).toBeDefined();

    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(workforceClient.approveWorkforceMission).toHaveBeenCalledWith(
        "MISSION-L6-TEST-001",
        expect.objectContaining({
          approverId: "raid",
          approverRole: "CHIEF_ARCHITECT",
          isHuman: true,
        })
      );
    });
  });

  it("6. Clicking 'Run Autonomous Loop' triggers orchestrateWorkforceMission API", async () => {
    workforceClient.orchestrateWorkforceMission.mockResolvedValue({
      mission: {
        ...mockLevel6Mission,
        current_iteration: 2,
      },
    });

    const activeMission = {
      ...mockLevel6Mission,
      status: "EXECUTING",
    };

    render(<MissionDetailModal isOpen={true} onClose={vi.fn()} mission={activeMission} />);

    const runBtn = screen.getByTestId("run-autonomous-loop-btn");
    expect(runBtn).toBeDefined();

    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(workforceClient.orchestrateWorkforceMission).toHaveBeenCalledWith("MISSION-L6-TEST-001");
    });
  });
});

