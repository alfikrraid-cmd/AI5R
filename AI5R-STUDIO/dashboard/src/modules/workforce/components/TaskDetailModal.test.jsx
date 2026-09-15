import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as workforceClient from "../../../api/workforceClient";
import TaskDetailModal from "./TaskDetailModal";

describe("TaskDetailModal - Phase 1F R1 Execution Seam", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const claimedTask = {
    work_item_id: "WORK-TASK-101",
    title: "Design Microservice Architecture",
    description: "Specify bounded contexts and domain events",
    assigned_position_id: "SOLUTION_ARCHITECT",
    assigned_employee_id: "EMP-ARCH-001",
    status: "CLAIMED",
    is_production: false,
    metadata: {},
  };

  const unclaimedTask = {
    work_item_id: "WORK-TASK-102",
    title: "Unclaimed Backlog Item",
    description: "Pending assignment",
    assigned_position_id: "BACKEND_ENGINEER",
    assigned_employee_id: null,
    status: "PUBLISHED",
    is_production: false,
    metadata: {},
  };

  const completedTask = {
    work_item_id: "WORK-TASK-103",
    title: "Implement Caching Layer",
    description: "Redis cluster setup",
    assigned_position_id: "BACKEND_ENGINEER",
    assigned_employee_id: "EMP-BE-001",
    status: "COMPLETED",
    is_production: false,
    artifact_id: "ART-ABC-123",
    artifact: {
      artifact_id: "ART-ABC-123",
      role: "BACKEND_ENGINEER",
      status: "SUCCESS",
      summary: "Completed Redis caching analysis and key eviction strategy.",
      output: {
        deliverables: "Propose Redis Cluster with 3 shards and LRU policy.",
        findings: ["Cache miss rate anticipated < 5%", "Session TTL set to 15m"],
        risks_and_considerations: ["Cache stampede on restart"],
      },
      started_at: "2026-09-15T12:00:00Z",
      completed_at: "2026-09-15T12:00:05Z",
      provider_metadata: { provider: "Router" },
    },
    metadata: {},
  };

  // 1. Eligible task exposes Run Analysis
  it("1. eligible claimed task exposes 'Run Analysis' button", () => {
    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={claimedTask}
      />
    );

    const runBtn = screen.getByTestId("run-analysis-button");
    expect(runBtn).toBeDefined();
    expect(runBtn.textContent).toContain("Run Analysis");
  });

  // 2. Unclaimed task does not expose Run Analysis
  it("2. unclaimed (published) task does not expose 'Run Analysis' button", () => {
    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={unclaimedTask}
      />
    );

    expect(screen.queryByTestId("run-analysis-button")).toBeNull();
  });

  // 3. Completed task does not expose Run Analysis
  it("3. completed task does not expose 'Run Analysis' button", () => {
    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={completedTask}
      />
    );

    expect(screen.queryByTestId("run-analysis-button")).toBeNull();
  });

  // 4. Double click prevented while executing
  it("4. double click is prevented and button enters loading state", async () => {
    let resolvePromise;
    const pendingPromise = new Promise((res) => {
      resolvePromise = res;
    });

    const executeSpy = vi
      .spyOn(workforceClient, "executeWorkforceTask")
      .mockReturnValue(pendingPromise);

    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={claimedTask}
      />
    );

    const runBtn = screen.getByTestId("run-analysis-button");
    fireEvent.click(runBtn);

    // Button should now be disabled and text updated
    expect(runBtn.disabled).toBe(true);
    expect(runBtn.textContent).toContain("Running Analysis...");

    // Clicking again while disabled must not fire additional calls
    fireEvent.click(runBtn);
    expect(executeSpy).toHaveBeenCalledTimes(1);

    // Resolve execution
    resolvePromise({
      status: "COMPLETED",
      work_item: { ...claimedTask, status: "COMPLETED", artifact_id: "ART-NEW-01" },
      artifact: {
        artifact_id: "ART-NEW-01",
        role: "SOLUTION_ARCHITECT",
        status: "SUCCESS",
        summary: "Architecture analysis finished.",
        output: {},
      },
    });

    await waitFor(() => {
      expect(screen.queryByTestId("run-analysis-button")).toBeNull();
    });
  });

  // 5. Execution error is displayed in banner
  it("5. execution error is displayed in execution error banner", async () => {
    vi.spyOn(workforceClient, "executeWorkforceTask").mockRejectedValue(
      new Error("AI provider rate limit exceeded (HTTP 429)")
    );

    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={claimedTask}
      />
    );

    const runBtn = screen.getByTestId("run-analysis-button");
    fireEvent.click(runBtn);

    await waitFor(() => {
      const banner = screen.getByTestId("execution-error-banner");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("AI provider rate limit exceeded");
    });
  });

  // 6. Artifact displayed cleanly
  it("6. artifact is displayed with summary, deliverables, findings, and risks", () => {
    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={completedTask}
      />
    );

    const artView = screen.getByTestId("execution-artifact-view");
    expect(artView).toBeDefined();
    expect(screen.getByText(/Completed Redis caching analysis/)).toBeDefined();
    expect(screen.getByText(/Propose Redis Cluster/)).toBeDefined();
    expect(screen.getByText(/Cache miss rate anticipated < 5%/)).toBeDefined();
    expect(screen.getByText(/Cache stampede on restart/)).toBeDefined();
    expect(screen.getByText(/ART-ABC-123/)).toBeDefined();
  });

  // 7. Real activity callback reflected
  it("7. onTaskExecuted callback is invoked on successful execution", async () => {
    const onTaskExecutedSpy = vi.fn();
    const mockArtifact = {
      artifact_id: "ART-999",
      role: "SOLUTION_ARCHITECT",
      status: "SUCCESS",
      summary: "Validated data contracts.",
      output: { deliverables: "Schema design" },
    };

    vi.spyOn(workforceClient, "executeWorkforceTask").mockResolvedValue({
      status: "COMPLETED",
      work_item: { ...claimedTask, status: "COMPLETED", artifact_id: "ART-999" },
      artifact: mockArtifact,
    });

    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={claimedTask}
        onTaskExecuted={onTaskExecutedSpy}
      />
    );

    const runBtn = screen.getByTestId("run-analysis-button");
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(onTaskExecutedSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "COMPLETED",
          artifact: expect.objectContaining({ artifact_id: "ART-999" }),
        })
      );
      expect(screen.getByTestId("execution-artifact-view")).toBeDefined();
    });
  });

  // 8. Production completion does not imply release
  it("8. completing a production task keeps status COMPLETED and does not release", async () => {
    const prodClaimedTask = {
      ...claimedTask,
      is_production: true,
    };

    vi.spyOn(workforceClient, "executeWorkforceTask").mockResolvedValue({
      status: "COMPLETED",
      work_item: { ...prodClaimedTask, status: "COMPLETED", artifact_id: "ART-PROD-01" },
      artifact: {
        artifact_id: "ART-PROD-01",
        role: "DEVOPS_ENGINEER",
        status: "SUCCESS",
        summary: "Deployment risk analysis complete.",
        output: {},
      },
    });

    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={prodClaimedTask}
      />
    );

    const runBtn = screen.getByTestId("run-analysis-button");
    fireEvent.click(runBtn);

    await waitFor(() => {
      // Must show WAITING CHIEF APPROVAL banner
      expect(screen.getByTestId("task-awaiting-chief-banner")).toBeDefined();
      expect(screen.getByText("COMPLETED")).toBeDefined();
      expect(screen.queryByText("RELEASED")).toBeNull();
    });
  });

  // 9. Chief approval remains separate
  it("9. Chief authorization button triggers onRequestApproval callback", () => {
    const onRequestApprovalSpy = vi.fn();
    const prodCompletedTask = {
      ...completedTask,
      is_production: true,
      metadata: { is_production: true },
    };

    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={prodCompletedTask}
        onRequestApproval={onRequestApprovalSpy}
      />
    );

    const authBtn = screen.getByTestId("open-approval-from-detail-button");
    expect(authBtn).toBeDefined();
    fireEvent.click(authBtn);
    expect(onRequestApprovalSpy).toHaveBeenCalledWith(expect.objectContaining({ is_production: true }));
  });

  // 10. No deploy/write controls introduced
  it("10. modal introduces no deploy, shell, or file write controls", () => {
    render(
      <TaskDetailModal
        isOpen={true}
        onClose={vi.fn()}
        task={claimedTask}
      />
    );

    // Verify absence of write / deploy buttons
    expect(screen.queryByText(/Deploy to Production/i)).toBeNull();
    expect(screen.queryByText(/Push to Git/i)).toBeNull();
    expect(screen.queryByText(/Execute Shell/i)).toBeNull();
    expect(screen.queryByText(/Commit Changes/i)).toBeNull();
  });
});
