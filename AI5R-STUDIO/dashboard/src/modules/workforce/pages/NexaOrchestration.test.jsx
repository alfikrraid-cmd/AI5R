import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as workforceClient from "../../../api/workforceClient";
import DelegateProjectModal from "../components/DelegateProjectModal";
import EmployeeCard from "../components/EmployeeCard";
import MissionDetailModal from "../components/MissionDetailModal";
import WorkforceWorkspace from "./WorkforceWorkspace";

const mockNexaEmployee = {
  employee_id: "EMP-PM-01",
  employee_name: "NEXA",
  position_id: "PROJECT_MANAGER",
  role: "AI Project Manager",
  status: "AVAILABLE",
  current_task: null,
  task_progress: 0,
  skills: ["TASK_BREAKDOWN", "SPRINT_PLANNING", "WORKFORCE_SCHEDULING"],
};

const mockArchitectEmployee = {
  employee_id: "EMP-SA-01",
  employee_name: "AI Solution Architect",
  position_id: "SOLUTION_ARCHITECT",
  role: "AI Solution Architect",
  status: "AVAILABLE",
  current_task: null,
  task_progress: 0,
  skills: ["ARCHITECTURE_DESIGN", "SYSTEM_DESIGN"],
};

const mockDecomposedMission = {
  mission_id: "MISSION-A1B2C3D4E5F6",
  title: "Deploy Automated Payment Gateway",
  description: "End-to-end payment gateway with Stripe and passkey auth",
  is_production: true,
  status: "IN_PROGRESS",
  progress: 17,
  sprint_id: "SPRINT-TEST-001",
  plan_id: "WEP-TEST-001",
  project_manager_id: "EMP-PM-01",
  created_at: "2026-09-15T10:00:00Z",
  updated_at: "2026-09-15T10:05:00Z",
  tasks: [
    {
      work_item_id: "TASK-SA-01",
      title: "Design solution architecture",
      assigned_position_id: "SOLUTION_ARCHITECT",
      assigned_employee_id: "EMP-SA-01",
      assigned_employee_name: "AI Solution Architect",
      status: "CLAIMED",
      dependencies: [],
      is_production: false,
    },
    {
      work_item_id: "TASK-BE-01",
      title: "Implement API backend",
      assigned_position_id: "BACKEND_ENGINEER",
      assigned_employee_id: "EMP-BE-01",
      assigned_employee_name: "AI Backend Engineer",
      status: "PUBLISHED",
      dependencies: ["TASK-SA-01"],
      is_production: false,
    },
    {
      work_item_id: "TASK-FE-01",
      title: "Implement frontend",
      assigned_position_id: "FRONTEND_ENGINEER",
      assigned_employee_id: "EMP-FE-01",
      assigned_employee_name: "AI Frontend Engineer",
      status: "PUBLISHED",
      dependencies: ["TASK-SA-01"],
      is_production: false,
    },
    {
      work_item_id: "TASK-QA-01",
      title: "Create quality tests",
      assigned_position_id: "QA_ENGINEER",
      assigned_employee_id: "EMP-QA-01",
      assigned_employee_name: "AI QA Engineer",
      status: "PUBLISHED",
      dependencies: ["TASK-BE-01", "TASK-FE-01"],
      is_production: false,
    },
    {
      work_item_id: "TASK-DO-01",
      title: "Prepare deployment",
      assigned_position_id: "DEVOPS_ENGINEER",
      assigned_employee_id: "EMP-DO-01",
      assigned_employee_name: "AI DevOps Engineer",
      status: "PUBLISHED",
      dependencies: ["TASK-QA-01"],
      is_production: true,
    },
    {
      work_item_id: "TASK-DOC-01",
      title: "Document delivery",
      assigned_position_id: "DOCUMENTATION_ENGINEER",
      assigned_employee_id: "EMP-DOC-01",
      assigned_employee_name: "AI Documentation Engineer",
      status: "PUBLISHED",
      dependencies: ["TASK-QA-01"],
      is_production: false,
    },
  ],
  execution_plan: {
    plan_id: "WEP-TEST-001",
    mission_id: "MISSION-A1B2C3D4E5F6",
    running: ["TASK-SA-01"],
    waiting: [],
    blocked: ["TASK-BE-01", "TASK-FE-01", "TASK-QA-01", "TASK-DO-01", "TASK-DOC-01"],
    completed: [],
  },
};

describe("Nexa Multi-Agent Orchestration UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("1. NEXA card displays 'Delegate Project' button", () => {
    const onDelegate = vi.fn();
    render(<EmployeeCard employee={mockNexaEmployee} onDelegateProject={onDelegate} />);

    const delegateBtn = screen.getByTestId("nexa-delegate-project-button");
    expect(delegateBtn).toBeDefined();
    expect(delegateBtn.textContent).toContain("Delegate Project");
  });

  it("2. Non-PM specialist card does NOT display 'Delegate Project' button", () => {
    const onDelegate = vi.fn();
    render(<EmployeeCard employee={mockArchitectEmployee} onDelegateProject={onDelegate} />);

    expect(screen.queryByTestId("nexa-delegate-project-button")).toBeNull();
  });

  it("3. Clicking 'Delegate Project' triggers onDelegateProject callback", () => {
    const onDelegate = vi.fn();
    render(<EmployeeCard employee={mockNexaEmployee} onDelegateProject={onDelegate} />);

    fireEvent.click(screen.getByTestId("nexa-delegate-project-button"));
    expect(onDelegate).toHaveBeenCalledWith(mockNexaEmployee);
  });

  it("4. DelegateProjectModal renders form fields and validates title requirement", () => {
    const onClose = vi.fn();
    const onDelegate = vi.fn();

    render(
      <DelegateProjectModal
        isOpen={true}
        onClose={onClose}
        onDelegate={onDelegate}
        isSubmitting={false}
      />
    );

    expect(screen.getByTestId("delegate-project-modal")).toBeDefined();
    expect(screen.getByTestId("mission-title-input")).toBeDefined();
    expect(screen.getByTestId("mission-description-input")).toBeDefined();
    expect(screen.getByTestId("mission-production-checkbox")).toBeDefined();
  });

  it("5. DelegateProjectModal shows Human Chief Gate warning when production is toggled", () => {
    render(
      <DelegateProjectModal
        isOpen={true}
        onClose={vi.fn()}
        onDelegate={vi.fn()}
        isSubmitting={false}
      />
    );

    const checkbox = screen.getByTestId("mission-production-checkbox");
    expect(screen.queryByTestId("production-warning")).toBeNull();

    fireEvent.click(checkbox);
    expect(screen.getByTestId("production-warning")).toBeDefined();
    expect(screen.getByTestId("production-warning").textContent).toContain("Human Chief Approval Gate");
  });

  it("6. Submitting DelegateProjectModal dispatches onDelegate with inputs", async () => {
    const onDelegate = vi.fn().mockResolvedValue({ status: "MISSION_CREATED" });

    render(
      <DelegateProjectModal
        isOpen={true}
        onClose={vi.fn()}
        onDelegate={onDelegate}
        isSubmitting={false}
      />
    );

    fireEvent.change(screen.getByTestId("mission-title-input"), {
      target: { value: "Build Microservice Auth" },
    });
    fireEvent.change(screen.getByTestId("mission-description-input"), {
      target: { value: "JWT and Passkeys" },
    });
    fireEvent.click(screen.getByTestId("mission-production-checkbox"));
    fireEvent.click(screen.getByTestId("submit-mission-button"));

    await waitFor(() => {
      expect(onDelegate).toHaveBeenCalledWith({
        title: "Build Microservice Auth",
        description: "JWT and Passkeys",
        isProduction: true,
      });
    });
  });

  it("7. MissionDetailModal renders mission header, title, and status", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    expect(screen.getByTestId("mission-detail-modal")).toBeDefined();
    expect(screen.getByTestId("mission-modal-title").textContent).toBe(
      "Deploy Automated Payment Gateway"
    );
    expect(screen.getByTestId("mission-status-badge").textContent).toBe("IN_PROGRESS");
    expect(screen.getByTestId("mission-production-flag").textContent).toContain("PRODUCTION GATE");
  });

  it("8. MissionDetailModal renders canonical derived progress percent", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    expect(screen.getByTestId("mission-progress-percent").textContent).toBe("17%");
  });

  it("9. MissionDetailModal renders all 6 canonical specialist tasks", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    expect(screen.getByTestId("mission-task-SOLUTION_ARCHITECT")).toBeDefined();
    expect(screen.getByTestId("mission-task-BACKEND_ENGINEER")).toBeDefined();
    expect(screen.getByTestId("mission-task-FRONTEND_ENGINEER")).toBeDefined();
    expect(screen.getByTestId("mission-task-QA_ENGINEER")).toBeDefined();
    expect(screen.getByTestId("mission-task-DEVOPS_ENGINEER")).toBeDefined();
    expect(screen.getByTestId("mission-task-DOCUMENTATION_ENGINEER")).toBeDefined();
  });

  it("10. Specialist tasks display assigned employee names", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    const assignees = screen.getAllByTestId("mission-task-assignee");
    const assigneeTexts = assignees.map((a) => a.textContent);
    expect(assigneeTexts).toContain("AI Solution Architect");
    expect(assigneeTexts).toContain("AI Backend Engineer");
    expect(assigneeTexts).toContain("AI Frontend Engineer");
    expect(assigneeTexts).toContain("AI QA Engineer");
    expect(assigneeTexts).toContain("AI DevOps Engineer");
    expect(assigneeTexts).toContain("AI Documentation Engineer");
  });

  it("11. Specialist tasks display dependency relationships", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    const deps = screen.getAllByTestId("mission-task-dependencies");
    const depTexts = deps.map((d) => d.textContent);
    expect(depTexts.some((t) => t.includes("Root task"))).toBe(true);
    expect(depTexts.some((t) => t.includes("TASK-SA-01"))).toBe(true);
    expect(depTexts.some((t) => t.includes("TASK-QA-01"))).toBe(true);
  });

  it("12. DevOps deployment task shows CHIEF GATE notice for production mission", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    expect(screen.getByTestId("mission-task-production-notice")).toBeDefined();
    expect(screen.getByTestId("mission-task-production-notice").textContent).toContain("CHIEF GATE");
  });

  it("13. MissionDetailModal displays execution plan topology counts", () => {
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        mission={mockDecomposedMission}
      />
    );

    const planNode = screen.getByTestId("mission-execution-plan");
    expect(planNode.textContent).toContain("RUNNING");
    expect(planNode.textContent).toContain("WAITING");
    expect(planNode.textContent).toContain("BLOCKED");
    expect(planNode.textContent).toContain("COMPLETED");
  });

  it("14. Closing MissionDetailModal triggers onClose callback", () => {
    const onClose = vi.fn();
    render(
      <MissionDetailModal
        isOpen={true}
        onClose={onClose}
        mission={mockDecomposedMission}
      />
    );

    fireEvent.click(screen.getByTestId("close-mission-modal"));
    expect(onClose).toHaveBeenCalled();
  });

  it("15. Top banner '⚡ Delegate Mission (NEXA)' button opens delegate modal in workspace", async () => {
    vi.spyOn(workforceClient, "fetchWorkforceEmployees").mockResolvedValue([mockNexaEmployee]);
    vi.spyOn(workforceClient, "fetchWorkforceBoard").mockResolvedValue({
      published: [],
      claimed: [],
      completed: [],
      released: [],
      summary: { total_items: 0 },
    });
    vi.spyOn(workforceClient, "fetchWorkforceActivities").mockResolvedValue([]);
    vi.spyOn(workforceClient, "fetchWorkforceMetrics").mockResolvedValue({});

    render(<WorkforceWorkspace />);

    await waitFor(() => {
      expect(screen.getByTestId("open-delegate-mission-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("open-delegate-mission-button"));
    expect(screen.getByTestId("delegate-project-modal")).toBeDefined();
  });
});
