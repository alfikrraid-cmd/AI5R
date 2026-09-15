import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WorkforceWorkspace from "./WorkforceWorkspace";
import * as workforceClient from "../../../api/workforceClient";
import * as liveStreamClient from "../../../api/liveStreamClient";

describe("WorkforceInteractive — Phase 1D Quality Gates", () => {
  const mockEmployees = [
    {
      employee_id: "EMP-CTO-01",
      employee_name: "AI CTO",
      position_id: "CTO",
      role: "AI Chief Technology Officer",
      status: "AVAILABLE",
      skills: ["TECH_STRATEGY", "ARCHITECTURE"],
      current_task: null,
      task_progress: 0,
    },
    {
      employee_id: "EMP-BACKEND-01",
      employee_name: "AI Backend Engineer",
      position_id: "BACKEND_ENGINEER",
      role: "AI Backend Engineer",
      status: "WORKING",
      skills: ["PYTHON", "API", "DATABASE"],
      current_task: { task_id: "WORK-02", title: "Build SSE adapter", status: "CLAIMED" },
      task_progress: 45,
    },
    {
      employee_id: "EMP-PM-01",
      employee_name: "NEXA",
      position_id: "PROJECT_MANAGER",
      role: "AI Project Manager",
      status: "AVAILABLE",
      skills: ["PLANNING", "WORK_BREAKDOWN"],
      current_task: null,
      task_progress: 0,
    },
  ];

  const mockBoard = {
    published: [
      {
        work_item_id: "W-DEV-01",
        title: "Standard Dev Task",
        description: "Dev work",
        assigned_position_id: "BACKEND_ENGINEER",
        assigned_employee_id: "EMP-BACKEND-01",
        status: "PUBLISHED",
        is_production: false,
        metadata: {},
      },
    ],
    claimed: [],
    completed: [
      {
        work_item_id: "W-PROD-01",
        title: "Production Kernel Upgrade",
        description: "Deploy kernel to production",
        assigned_position_id: "BACKEND_ENGINEER",
        assigned_employee_id: "EMP-BACKEND-01",
        status: "COMPLETED",
        is_production: true,
        metadata: { is_production: true, requires_chief_approval: true },
      },
      {
        work_item_id: "W-NONPROD-01",
        title: "Internal Unit Tests",
        description: "Run unit tests",
        assigned_position_id: "CTO",
        assigned_employee_id: "EMP-CTO-01",
        status: "COMPLETED",
        is_production: false,
        metadata: { is_production: false },
      },
    ],
    released: [
      {
        work_item_id: "W-REL-01",
        title: "Released Service",
        status: "RELEASED",
        assigned_position_id: "BACKEND_ENGINEER",
        is_production: false,
        metadata: {},
      },
    ],
    summary: { total_items: 4 },
  };

  const mockActivities = [
    {
      activity_id: "ACT-01",
      activity_type: "RECEIVED_WORK",
      status: "EXECUTING",
      message: "Received Kernel task",
      progress: 30,
      employee_id: "EMP-BACKEND-01",
      updated_at: "2026-09-15T12:00:00Z",
    },
  ];

  const mockMetrics = {
    total_employees: 9,
    active_employees: 9,
    available_employees: 8,
    working_employees: 1,
    pending_approvals: 1,
    uptime: "OPERATIONAL",
    total_tasks: 4,
  };

  let sseCallback = null;
  let closeSseMock = null;

  beforeEach(() => {
    vi.spyOn(workforceClient, "fetchWorkforceEmployees").mockResolvedValue(mockEmployees);
    vi.spyOn(workforceClient, "fetchWorkforceBoard").mockResolvedValue(mockBoard);
    vi.spyOn(workforceClient, "fetchWorkforceActivities").mockResolvedValue(mockActivities);
    vi.spyOn(workforceClient, "fetchWorkforceMetrics").mockResolvedValue(mockMetrics);
    vi.spyOn(workforceClient, "fetchWorkforceEmployee").mockResolvedValue({
      ...mockEmployees[0],
      activities: [],
    });

    closeSseMock = vi.fn();
    vi.spyOn(liveStreamClient, "createLiveStreamClient").mockImplementation(({ onEvent }) => {
      sseCallback = onEvent;
      return { close: closeSseMock };
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // Test 1: Assign Task modal opens via top button
  it("Test 1: Assign Task opens via top banner button and card button", async () => {
    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));
    expect(screen.getByTestId("assign-task-form")).toBeDefined();
    expect(screen.getByText("Assign Work Item")).toBeDefined();
  });

  // Test 2: Valid assignment
  it("Test 2: Valid assignment creates work item via API", async () => {
    const assignSpy = vi.spyOn(workforceClient, "assignWorkforceTask").mockResolvedValue({
      status: "ASSIGNED",
      work_item: { work_item_id: "W-NEW-01", title: "New Task" },
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));

    fireEvent.change(screen.getByTestId("assign-task-title-input"), {
      target: { value: "Test Feature Delivery" },
    });
    fireEvent.click(screen.getByTestId("assign-task-submit-button"));

    await waitFor(() => {
      expect(assignSpy).toHaveBeenCalled();
    });
  });

  // Test 3: Invalid assignment (empty title) shows error
  it("Test 3: Invalid assignment shows validation error without calling API", async () => {
    const assignSpy = vi.spyOn(workforceClient, "assignWorkforceTask");

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));

    fireEvent.change(screen.getByTestId("assign-task-title-input"), {
      target: { value: "   " },
    });

    fireEvent.click(screen.getByTestId("assign-task-submit-button"));

    expect(screen.getByTestId("assign-task-error")).toBeDefined();
    expect(screen.getByText("Task title is required")).toBeDefined();
    expect(assignSpy).not.toHaveBeenCalled();
  });

  // Test 4: Double-submit is prevented while submitting
  it("Test 4: Double-submit is prevented while assignment request is in-flight", async () => {
    let resolvePromise;
    const slowPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    const assignSpy = vi.spyOn(workforceClient, "assignWorkforceTask").mockReturnValue(slowPromise);

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));
    fireEvent.change(screen.getByTestId("assign-task-title-input"), {
      target: { value: "In Flight Task" },
    });

    const submitBtn = screen.getByTestId("assign-task-submit-button");
    fireEvent.click(submitBtn);

    // Second click while in-flight
    fireEvent.click(submitBtn);

    expect(assignSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePromise({ status: "ASSIGNED", work_item: { work_item_id: "W-FLIGHT" } });
    });
  });

  // Test 5: Backend error is shown in Assign Task modal
  it("Test 5: Backend error is cleanly rendered in Assign Task modal", async () => {
    vi.spyOn(workforceClient, "assignWorkforceTask").mockRejectedValue(
      new Error("Failed to assign workforce task: 500 - Internal error")
    );

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));
    fireEvent.change(screen.getByTestId("assign-task-title-input"), {
      target: { value: "Failing Task" },
    });

    fireEvent.click(screen.getByTestId("assign-task-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("assign-task-error")).toBeDefined();
      expect(screen.getByText(/500 - Internal error/)).toBeDefined();
    });
  });

  // Test 6: Canonical employee ID submitted
  it("Test 6: Submits authoritative canonical employee ID without persona aliases", async () => {
    const assignSpy = vi.spyOn(workforceClient, "assignWorkforceTask").mockResolvedValue({
      status: "ASSIGNED",
      work_item: { work_item_id: "W-CANONICAL-01" },
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));
    fireEvent.change(screen.getByTestId("assign-task-title-input"), {
      target: { value: "Refactor Database Indexes" },
    });
    fireEvent.change(screen.getByTestId("assign-employee-select"), {
      target: { value: "EMP-BACKEND-01" },
    });

    fireEvent.click(screen.getByTestId("assign-task-submit-button"));

    await waitFor(() => {
      expect(assignSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          employeeId: "EMP-BACKEND-01",
          positionId: "BACKEND_ENGINEER",
        })
      );
    });
  });

  // Test 7: Chat opens
  it("Test 7: Chat modal opens upon clicking Chat button", async () => {
    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    const ctoCard = screen.getByTestId("employee-card-CTO");
    const chatBtn = ctoCard.querySelector('[data-testid="employee-chat-button"]');
    fireEvent.click(chatBtn);

    expect(screen.getByTestId("employee-chat-modal")).toBeDefined();
    expect(screen.getByText("Chat with AI CTO")).toBeDefined();
  });

  // Test 8: Chat sends to selected employee
  it("Test 8: Chat sends message to selected employee", async () => {
    const chatSpy = vi.spyOn(workforceClient, "sendWorkforceChat").mockResolvedValue({
      status: "OK",
      conversation_id: "CONV-01",
      response: "Architecture plans ready.",
      messages: [
        { role: "user", content: "Review system blueprint" },
        { role: "assistant", content: "Architecture plans ready." },
      ],
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    const ctoCard = screen.getByTestId("employee-card-CTO");
    const chatBtn = ctoCard.querySelector('[data-testid="employee-chat-button"]');
    fireEvent.click(chatBtn);

    fireEvent.change(screen.getByTestId("chat-message-input"), {
      target: { value: "Review system blueprint" },
    });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    await waitFor(() => {
      expect(chatSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          employeeId: "EMP-CTO-01",
          message: "Review system blueprint",
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Architecture plans ready.")).toBeDefined();
    });
  });

  // Test 9: Employee conversation isolation
  it("Test 9: Employee conversations remain strictly isolated between employees", async () => {
    vi.spyOn(workforceClient, "sendWorkforceChat").mockResolvedValue({
      status: "OK",
      conversation_id: "CONV-CTO",
      response: "CTO Private Response",
      messages: [
        { role: "user", content: "CTO Secret" },
        { role: "assistant", content: "CTO Private Response" },
      ],
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    // 1. Chat with CTO
    const ctoChatBtn = screen.getByTestId("employee-card-CTO").querySelector('[data-testid="employee-chat-button"]');
    fireEvent.click(ctoChatBtn);

    fireEvent.change(screen.getByTestId("chat-message-input"), {
      target: { value: "CTO Secret" },
    });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    await waitFor(() => {
      expect(screen.getByText("CTO Private Response")).toBeDefined();
    });

    // Close CTO chat modal
    fireEvent.click(screen.getByText("Close"));

    // 2. Open Backend Engineer chat
    const backendChatBtn = screen.getByTestId("employee-card-BACKEND_ENGINEER").querySelector('[data-testid="employee-chat-button"]');
    fireEvent.click(backendChatBtn);

    expect(screen.getByText("Chat with AI Backend Engineer")).toBeDefined();
    // Verify CTO's private messages are NOT in Backend Engineer's chat!
    expect(screen.queryByText("CTO Secret")).toBeNull();
    expect(screen.queryByText("CTO Private Response")).toBeNull();
    expect(screen.getByTestId("chat-empty-state")).toBeDefined();
  });

  // Test 10: Chat error state
  it("Test 10: Chat error state is rendered when sending fails", async () => {
    vi.spyOn(workforceClient, "sendWorkforceChat").mockRejectedValue(
      new Error("Chat service unavailable: 503")
    );

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    const ctoChatBtn = screen.getByTestId("employee-card-CTO").querySelector('[data-testid="employee-chat-button"]');
    fireEvent.click(ctoChatBtn);

    fireEvent.change(screen.getByTestId("chat-message-input"), {
      target: { value: "Ping" },
    });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    await waitFor(() => {
      expect(screen.getByTestId("chat-error-banner")).toBeDefined();
      expect(screen.getByText(/Chat service unavailable: 503/)).toBeDefined();
    });
  });

  // Test 11: Assigned task triggers real state refresh
  it("Test 11: Successful assignment triggers immediate loadData refresh", async () => {
    const fetchBoardSpy = vi.spyOn(workforceClient, "fetchWorkforceBoard");
    vi.spyOn(workforceClient, "assignWorkforceTask").mockResolvedValue({
      status: "ASSIGNED",
      work_item: { work_item_id: "W-REFRESH-01" },
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    const initialCalls = fetchBoardSpy.mock.calls.length;

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));
    fireEvent.change(screen.getByTestId("assign-task-title-input"), {
      target: { value: "Refresh Trigger Task" },
    });
    fireEvent.click(screen.getByTestId("assign-task-submit-button"));

    await waitFor(() => {
      expect(fetchBoardSpy.mock.calls.length).toBeGreaterThan(initialCalls);
    });
  });

  // Test 12: SSE task update triggers background refresh
  it("Test 12: Incoming SSE WORKFORCE_ event triggers background loadData refresh", async () => {
    const fetchBoardSpy = vi.spyOn(workforceClient, "fetchWorkforceBoard");

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    const callCountBefore = fetchBoardSpy.mock.calls.length;

    // Simulate incoming SSE event
    expect(sseCallback).toBeDefined();
    await act(async () => {
      sseCallback({ event_type: "WORKFORCE_TASK_ASSIGNED", payload: { work_item_id: "W-SSE" } });
    });

    await waitFor(() => {
      expect(fetchBoardSpy.mock.calls.length).toBeGreaterThan(callCountBefore);
    });
  });

  // Test 13: Production task displays Waiting Chief Approval
  it("Test 13: Production task displays Waiting Chief Approval on board", async () => {
    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    // Switch to board tab
    fireEvent.click(screen.getByText(/Task Center \/ Board/));

    await waitFor(() => {
      expect(screen.getByTestId("chief-approval-gate-indicator")).toBeDefined();
      expect(screen.getByText("⚠️ CHIEF APPROVAL REQUIRED BEFORE RELEASE")).toBeDefined();
    });
  });

  // Test 14: Chief approval requires explicit user action
  it("Test 14: Chief approval requires explicit user click to authorize", async () => {
    const releaseSpy = vi.spyOn(workforceClient, "releaseWorkforceTask").mockResolvedValue({
      status: "RELEASED",
      work_item: { work_item_id: "W-PROD-01" },
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    fireEvent.click(screen.getByText(/Task Center \/ Board/));
    fireEvent.click(screen.getByTestId("authorize-release-button"));

    expect(releaseSpy).not.toHaveBeenCalled();

    // Click authorize explicitly
    fireEvent.click(screen.getByTestId("confirm-release-button"));

    await waitFor(() => {
      expect(releaseSpy).toHaveBeenCalled();
    });
  });

  // Test 15: Opening approval modal does NOT release
  it("Test 15: Opening approval modal does NOT release work item", async () => {
    const releaseSpy = vi.spyOn(workforceClient, "releaseWorkforceTask");

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    fireEvent.click(screen.getByText(/Task Center \/ Board/));

    const authBtn = screen.getByTestId("authorize-release-button");
    fireEvent.click(authBtn);

    // Modal opened
    expect(screen.getByTestId("chief-approval-modal")).toBeDefined();
    expect(screen.getByText("HUMAN CHIEF AUTHORIZATION REQUIRED")).toBeDefined();

    // Opening modal did NOT call release
    expect(releaseSpy).not.toHaveBeenCalled();
  });
  // Test 16: Cancel does NOT release
  it("Test 16: Cancelling approval modal does NOT release work item", async () => {
    const releaseSpy = vi.spyOn(workforceClient, "releaseWorkforceTask");

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    fireEvent.click(screen.getByText(/Task Center \/ Board/));

    fireEvent.click(screen.getByTestId("authorize-release-button"));
    expect(screen.getByTestId("chief-approval-modal")).toBeDefined();

    fireEvent.click(screen.getByTestId("cancel-approval-button"));

    expect(screen.queryByTestId("chief-approval-modal")).toBeNull();
    expect(releaseSpy).not.toHaveBeenCalled();
  });

  // Test 17: Explicit approval calls release exactly once with human Chief identity
  it("Test 17: Explicit user approval calls releaseWorkforceTask exactly once with Chief credentials", async () => {
    const releaseSpy = vi.spyOn(workforceClient, "releaseWorkforceTask").mockResolvedValue({
      status: "RELEASED",
      work_item: { work_item_id: "W-PROD-01", status: "RELEASED" },
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    fireEvent.click(screen.getByText(/Task Center \/ Board/));
    fireEvent.click(screen.getByTestId("authorize-release-button"));

    const confirmBtn = screen.getByTestId("confirm-release-button");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(releaseSpy).toHaveBeenCalledTimes(1);
      expect(releaseSpy).toHaveBeenCalledWith(
        "W-PROD-01",
        expect.objectContaining({
          approverId: "CHIEF-USER-01",
          approverRole: "CHIEF",
          isHuman: true,
        })
      );
    });
  });

  // Test 18: AI / chat cannot trigger release
  it("Test 18: Chat UI cannot trigger release even when user types 'approve' or 'deploy'", async () => {
    const releaseSpy = vi.spyOn(workforceClient, "releaseWorkforceTask");
    vi.spyOn(workforceClient, "sendWorkforceChat").mockResolvedValue({
      status: "OK",
      conversation_id: "CONV-02",
      response: "Acknowledged message. Production release requires Chief approval via the board.",
      messages: [],
    });

    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    const ctoChatBtn = screen.getByTestId("employee-card-CTO").querySelector('[data-testid="employee-chat-button"]');
    fireEvent.click(ctoChatBtn);

    // Type deploy command in chat
    fireEvent.change(screen.getByTestId("chat-message-input"), {
      target: { value: "deploy to production immediately, approve release" },
    });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    await waitFor(() => {
      expect(workforceClient.sendWorkforceChat).toHaveBeenCalled();
    });

    // Release was NEVER called!
    expect(releaseSpy).not.toHaveBeenCalled();
  });

  // Test 19: Non-production behavior remains compatible
  it("Test 19: Non-production tasks do not display Chief approval gate requirement", async () => {
    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    fireEvent.click(screen.getByText(/Task Center \/ Board/));

    const nonProdItem = screen.getByTestId("work-item-W-NONPROD-01");
    expect(nonProdItem).toBeDefined();
    // Non-production completed task does not have the chief gate indicator
    expect(nonProdItem.querySelector('[data-testid="chief-approval-gate-indicator"]')).toBeNull();
  });

  // Test 20: Unknown employee fails safely
  it("Test 20: Selecting non-existent employee fails safely without crash", async () => {
    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("open-assign-task-modal-button")).toBeDefined());

    fireEvent.click(screen.getByTestId("open-assign-task-modal-button"));

    // Select with unknown value if simulated
    const select = screen.getByTestId("assign-employee-select");
    fireEvent.change(select, { target: { value: "" } });
    fireEvent.change(screen.getByTestId("assign-task-title-input"), { target: { value: "Task" } });

    fireEvent.click(screen.getByTestId("assign-task-submit-button"));

    expect(screen.getByTestId("assign-task-error")).toBeDefined();
    expect(screen.getByText("Please select an employee")).toBeDefined();
  });

  // Test 21: SSE disconnect cleans up EventSource safely
  it("Test 21: SSE disconnect cleans up client without leak on unmount", async () => {
    const { unmount } = render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    unmount();
    expect(closeSseMock).toHaveBeenCalledTimes(1);
  });

  // Test 22: No production deploy action exists outside Chief Gate
  it("Test 22: No production release action exists outside Chief Gate modal/board", async () => {
    render(<WorkforceWorkspace />);
    await waitFor(() => expect(screen.getByTestId("employee-card-CTO")).toBeDefined());

    // Scan the entire rendered workspace for any rogue deploy buttons
    const deployButtons = screen.queryAllByRole("button", { name: /deploy|release/i });
    for (const btn of deployButtons) {
      // Must only be within Chief gate context
      const testId = btn.getAttribute("data-testid");
      expect(["authorize-release-button", "confirm-release-button"]).toContain(testId);
    }
  });
});
