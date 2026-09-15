import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  assignWorkforceTask,
  createWorkforceMission,
  executeWorkforceTask,
  fetchTaskArtifacts,
  fetchWorkforceActivities,
  fetchWorkforceArtifact,
  fetchWorkforceBoard,
  fetchWorkforceEmployee,
  fetchWorkforceEmployees,
  fetchWorkforceMetrics,
  fetchWorkforceMission,
  fetchWorkforceMissions,
  releaseWorkforceTask,
  sendWorkforceChat,
} from "./workforceClient";

describe("workforceClient", () => {
  let realFetch;

  beforeEach(() => {
    realFetch = global.fetch;
    window.localStorage.clear();
  });

  afterEach(() => {
    global.fetch = realFetch;
  });

  it("fetchWorkforceEmployees calls /api/workforce/employees and attaches bearer token", async () => {
    window.localStorage.setItem("ai5r.ltsa.session", JSON.stringify({ token: "test-jwt-token" }));

    const mockEmployees = [
      { employee_id: "EMP-001", employee_name: "AI CTO", position_id: "CTO" },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockEmployees),
    });

    const result = await fetchWorkforceEmployees();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/employees"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-jwt-token",
          Accept: "application/json",
        }),
      })
    );
    expect(result).toEqual(mockEmployees);
  });

  it("fetchWorkforceEmployee requires employeeId and fetches by ID", async () => {
    await expect(fetchWorkforceEmployee("")).rejects.toThrow("employeeId is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ employee_id: "EMP-CTO-01", position_id: "CTO" }),
    });

    const result = await fetchWorkforceEmployee("EMP-CTO-01");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/employees/EMP-CTO-01"),
      expect.anything()
    );
    expect(result.position_id).toBe("CTO");
  });

  it("fetchWorkforceBoard retrieves board columns", async () => {
    const mockBoard = {
      published: [],
      claimed: [],
      completed: [],
      released: [],
      summary: { total_items: 0 },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockBoard),
    });

    const result = await fetchWorkforceBoard();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/board"),
      expect.anything()
    );
    expect(result.summary.total_items).toBe(0);
  });

  it("fetchWorkforceActivities formats query parameters", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue([]),
    });

    await fetchWorkforceActivities({ limit: 25, employeeId: "EMP-001" });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/activities?limit=25&employee_id=EMP-001"),
      expect.anything()
    );
  });

  it("fetchWorkforceMetrics retrieves workforce metrics", async () => {
    const mockMetrics = {
      status: "OK",
      total_employees: 9,
      active_employees: 9,
      uptime: "OPERATIONAL",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockMetrics),
    });

    const result = await fetchWorkforceMetrics();
    expect(result.total_employees).toBe(9);
    expect(result.uptime).toBe("OPERATIONAL");
  });

  it("handles non-ok API responses gracefully with detailed error message", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: vi.fn().mockResolvedValue({ detail: "Employee not found" }),
    });

    await expect(fetchWorkforceEmployee("INVALID-ID")).rejects.toThrow(
      "Failed to fetch employee INVALID-ID: 404 - Employee not found"
    );
  });

  it("assignWorkforceTask validates title and sends POST /api/workforce/tasks/assign", async () => {
    await expect(assignWorkforceTask({ title: "" })).rejects.toThrow("Task title is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: "ASSIGNED", work_item: { work_item_id: "W-10" } }),
    });

    const res = await assignWorkforceTask({
      title: "Deploy Kernel",
      description: "Production release",
      positionId: "DEVOPS_ENGINEER",
      employeeId: "EMP-DEVOPS-01",
      isProduction: true,
      metadata: { sprint: "S-1" },
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/tasks/assign"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "Deploy Kernel",
          description: "Production release",
          position_id: "DEVOPS_ENGINEER",
          employee_id: "EMP-DEVOPS-01",
          is_production: true,
          metadata: { sprint: "S-1" },
        }),
      })
    );
    expect(res.status).toBe("ASSIGNED");
  });

  it("sendWorkforceChat validates inputs and sends POST /api/workforce/chat", async () => {
    await expect(sendWorkforceChat({ employeeId: "", message: "hi" })).rejects.toThrow(
      "employeeId is required"
    );
    await expect(
      sendWorkforceChat({ employeeId: "EMP-01", message: "  " })
    ).rejects.toThrow("Message is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({
        status: "OK",
        conversation_id: "CONV-123",
        response: "Acknowledged",
      }),
    });

    const res = await sendWorkforceChat({
      employeeId: "EMP-01",
      message: "Please inspect system logs",
      conversationId: "CONV-123",
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/chat"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          employee_id: "EMP-01",
          message: "Please inspect system logs",
          conversation_id: "CONV-123",
          metadata: {},
        }),
      })
    );
    expect(res.response).toBe("Acknowledged");
  });

  it("releaseWorkforceTask validates workItemId and sends POST with Chief identity", async () => {
    await expect(releaseWorkforceTask("")).rejects.toThrow("workItemId is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: "RELEASED" }),
    });

    const res = await releaseWorkforceTask("W-10", {
      approverId: "CHIEF-01",
      approverRole: "CHIEF",
      isHuman: true,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/tasks/W-10/release"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          approver_id: "CHIEF-01",
          approver_role: "CHIEF",
          is_human: true,
          metadata: {},
        }),
      })
    );
    expect(res.status).toBe("RELEASED");
  });

  it("createWorkforceMission validates title and posts payload to /api/workforce/missions", async () => {
    await expect(createWorkforceMission({ title: "  " })).rejects.toThrow("Mission title is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: "MISSION_CREATED", mission: { mission_id: "M-1" } }),
    });

    const res = await createWorkforceMission({
      title: "Launch Customer Gateway",
      description: "Setup API routes and auth",
      isProduction: true,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/missions"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "Launch Customer Gateway",
          description: "Setup API routes and auth",
          is_production: true,
          metadata: {},
        }),
      })
    );
    expect(res.status).toBe("MISSION_CREATED");
  });

  it("fetchWorkforceMissions calls GET /api/workforce/missions", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue([{ mission_id: "M-1" }]),
    });

    const res = await fetchWorkforceMissions();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/missions"),
      expect.anything()
    );
    expect(res).toEqual([{ mission_id: "M-1" }]);
  });

  it("fetchWorkforceMission validates missionId and calls GET /api/workforce/missions/{id}", async () => {
    await expect(fetchWorkforceMission("")).rejects.toThrow("missionId is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ mission_id: "M-1", title: "Gateway" }),
    });

    const res = await fetchWorkforceMission("M-1");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/missions/M-1"),
      expect.anything()
    );
    expect(res.title).toBe("Gateway");
  });

  it("executeWorkforceTask validates workItemId and calls POST /api/workforce/tasks/{id}/execute", async () => {
    await expect(executeWorkforceTask("")).rejects.toThrow("workItemId is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({
        status: "COMPLETED",
        artifact: { artifact_id: "ART-1", summary: "Analysis completed" },
      }),
    });

    const res = await executeWorkforceTask("WORK-123");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/tasks/WORK-123/execute"),
      expect.objectContaining({ method: "POST" })
    );
    expect(res.status).toBe("COMPLETED");
    expect(res.artifact.artifact_id).toBe("ART-1");
  });

  it("fetchTaskArtifacts validates workItemId and calls GET /api/workforce/tasks/{id}/artifacts", async () => {
    await expect(fetchTaskArtifacts("")).rejects.toThrow("workItemId is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue([{ artifact_id: "ART-1" }]),
    });

    const res = await fetchTaskArtifacts("WORK-123");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/tasks/WORK-123/artifacts"),
      expect.anything()
    );
    expect(res).toEqual([{ artifact_id: "ART-1" }]);
  });

  it("fetchWorkforceArtifact validates artifactId and calls GET /api/workforce/artifacts/{id}", async () => {
    await expect(fetchWorkforceArtifact("")).rejects.toThrow("artifactId is required");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ artifact_id: "ART-1", summary: "Foundations" }),
    });

    const res = await fetchWorkforceArtifact("ART-1");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/workforce/artifacts/ART-1"),
      expect.anything()
    );
    expect(res.summary).toBe("Foundations");
  });
});
