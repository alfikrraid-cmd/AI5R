import { describe, expect, it, vi } from "vitest";
import { runOrganizationGoal } from "./organizationClient";

describe("runOrganizationGoal", () => {
  it("posts to the organization goal endpoint and returns the real response", async () => {
    const responseBody = {
      product: "LTSA-BRAIN",
      product_status: "RUNNING",
      organization_runtime_id: "ORG-RUN-ORG-GOAL-001",
      organization_status: "ACTIVE",
      work_unit_count: 2,
      summary: { employees: ["EMP-EXECUTOR", "EMP-PLANNER"] },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(responseBody),
    });

    const result = await runOrganizationGoal("LTSA-BRAIN", "ORG-GOAL-001");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/organization/goal",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_name: "LTSA-BRAIN",
          goal_id: "ORG-GOAL-001",
        }),
      },
    );
    expect(result).toEqual(responseBody);
  });

  it("throws a real error when the request fails, instead of returning fake success data", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
    });

    await expect(
      runOrganizationGoal("LTSA-BRAIN", "ORG-GOAL-001"),
    ).rejects.toThrow("Organization API request failed: 503");
  });
});
