import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchWorkforceActivities,
  fetchWorkforceBoard,
  fetchWorkforceEmployee,
  fetchWorkforceEmployees,
  fetchWorkforceMetrics,
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
});

