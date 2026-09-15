import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WorkforceWorkspace from "./WorkforceWorkspace";
import * as workforceClient from "../../../api/workforceClient";
import * as liveStreamClient from "../../../api/liveStreamClient";

describe("WorkforceWorkspace", () => {
  const mockEmployees = [
    {
      employee_id: "EMP-001",
      employee_name: "AI CTO",
      position_id: "CTO",
      role: "AI Chief Technology Officer",
      status: "AVAILABLE",
      skills: ["TECH_STRATEGY", "ARCHITECTURE"],
      current_task: null,
      task_progress: 0,
    },
    {
      employee_id: "EMP-002",
      employee_name: "AI Backend Engineer",
      position_id: "BACKEND_ENGINEER",
      role: "AI Backend Engineer",
      status: "WORKING",
      skills: ["PYTHON", "API", "DATABASE"],
      current_task: { task_id: "WORK-02", title: "Build SSE adapter", status: "CLAIMED" },
      task_progress: 45,
    },
  ];

  const mockBoard = {
    published: [{ work_item_id: "W-1", title: "Task 1", assigned_position_id: "CTO" }],
    claimed: [{ work_item_id: "W-2", title: "Task 2", assigned_position_id: "BACKEND_ENGINEER" }],
    completed: [],
    released: [],
    summary: { total_items: 2 },
  };

  const mockActivities = [
    {
      activity_id: "ACT-01",
      activity_type: "EXECUTING",
      status: "EXECUTING",
      message: "Processing API request",
      progress: 50,
      employee_id: "EMP-002",
      updated_at: "2026-09-15T12:00:00Z",
    },
  ];

  const mockMetrics = {
    total_employees: 9,
    active_employees: 9,
    available_employees: 8,
    working_employees: 1,
    uptime: "OPERATIONAL",
    total_tasks: 2,
  };

  beforeEach(() => {
    vi.spyOn(workforceClient, "fetchWorkforceEmployees").mockResolvedValue(mockEmployees);
    vi.spyOn(workforceClient, "fetchWorkforceBoard").mockResolvedValue(mockBoard);
    vi.spyOn(workforceClient, "fetchWorkforceActivities").mockResolvedValue(mockActivities);
    vi.spyOn(workforceClient, "fetchWorkforceMetrics").mockResolvedValue(mockMetrics);
    vi.spyOn(workforceClient, "fetchWorkforceEmployee").mockResolvedValue({
      ...mockEmployees[0],
      activities: [],
    });
    vi.spyOn(liveStreamClient, "createLiveStreamClient").mockReturnValue({ close: vi.fn() });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("mounts workspace, displays metrics and employees grid", async () => {
    render(<WorkforceWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("AI EMPLOYEES & DIGITAL WORKFORCE")).toBeDefined();
    });

    await waitFor(() => {
      expect(screen.getByTestId("employee-card-CTO")).toBeDefined();
      expect(screen.getByTestId("employee-card-BACKEND_ENGINEER")).toBeDefined();
    });

    expect(screen.getByText("OPERATIONAL")).toBeDefined();
  });

  it("switches to Task Center / Board tab and renders board columns", async () => {
    render(<WorkforceWorkspace />);

    await waitFor(() => {
      expect(screen.getByTestId("employee-card-CTO")).toBeDefined();
    });

    const boardTab = screen.getByText(/Task Center \/ Board/);
    fireEvent.click(boardTab);

    expect(screen.getByTestId("workforce-board-view")).toBeDefined();
    expect(screen.getByText("Task 1")).toBeDefined();
    expect(screen.getByText("Task 2")).toBeDefined();
  });

  it("switches to Activity Feed tab and renders activities", async () => {
    render(<WorkforceWorkspace />);

    await waitFor(() => {
      expect(screen.getByTestId("employee-card-CTO")).toBeDefined();
    });

    const activityTab = screen.getByText(/Activity Feed/);
    fireEvent.click(activityTab);

    expect(screen.getByTestId("workforce-activity-feed")).toBeDefined();
    expect(screen.getByText("Processing API request")).toBeDefined();
  });

  it("filters employees via search box", async () => {
    render(<WorkforceWorkspace />);

    await waitFor(() => {
      expect(screen.getByTestId("employee-card-CTO")).toBeDefined();
      expect(screen.getByTestId("employee-card-BACKEND_ENGINEER")).toBeDefined();
    });

    const searchInput = screen.getByPlaceholderText("Search employee, role, skill...");
    fireEvent.change(searchInput, { target: { value: "Backend" } });

    expect(screen.queryByTestId("employee-card-CTO")).toBeNull();
    expect(screen.getByTestId("employee-card-BACKEND_ENGINEER")).toBeDefined();
  });

  it("opens employee detail modal on inspect click", async () => {
    render(<WorkforceWorkspace />);

    await waitFor(() => {
      expect(screen.getByTestId("employee-card-CTO")).toBeDefined();
    });

    const inspectButtons = screen.getAllByText("Inspect Profile");
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId("employee-detail-content")).toBeDefined();
    });
  });
});

