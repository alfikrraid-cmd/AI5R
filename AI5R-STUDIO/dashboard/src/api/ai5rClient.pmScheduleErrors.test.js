import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPMSchedule } from "./ai5rClient";

// AI5R-PHASE4E2, Section H -- the production PM workspace previously
// rendered "[object Object],[object Object]" on a create failure. Root
// cause: FastAPI's `detail` field is a STRING for a single HTTPException
// but a LIST of {loc, msg, type} objects for a Pydantic 422 validation
// error (e.g. PMScheduleCreateRequest.planned_activities's own validator,
// added in 4E.1) -- `new Error(detail)` on that list stringified each
// object element as "[object Object]" via the array's own toString().
// Proves createPMSchedule() now normalizes both shapes into a readable
// message instead.
function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("createPMSchedule error normalization", () => {
  it("surfaces a single HTTPException's string detail verbatim", async () => {
    global.fetch.mockResolvedValue(jsonResponse(404, { detail: "Canonical pump not found" }));

    await expect(createPMSchedule({ asset_code: "UNKNOWN-1" })).rejects.toThrow("Canonical pump not found");
  });

  it("normalizes a Pydantic 422 validation-error list into a readable message, never [object Object]", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(422, {
        detail: [
          { type: "value_error", loc: ["body", "planned_activities", 0, "code"], msg: "unknown planned activity code: 'NOT_REAL'" },
          { type: "missing", loc: ["body", "frequency"], msg: "Field required" },
        ],
      })
    );

    try {
      await createPMSchedule({ asset_code: "211-P-1A" });
      throw new Error("expected createPMSchedule to reject");
    } catch (error) {
      expect(error.message).not.toMatch(/object Object/i);
      expect(error.message).toContain("unknown planned activity code");
      expect(error.message).toContain("Field required");
    }
  });

  it("normalizes a duplicate/conflict response's detail without [object Object]", async () => {
    global.fetch.mockResolvedValue(jsonResponse(409, { detail: [{ msg: "A schedule for this pump already exists" }] }));

    try {
      await createPMSchedule({ asset_code: "211-P-1A" });
      throw new Error("expected createPMSchedule to reject");
    } catch (error) {
      expect(error.message).not.toMatch(/object Object/i);
      expect(error.message).toContain("A schedule for this pump already exists");
    }
  });

  it("falls back to a generic message when detail is missing entirely", async () => {
    global.fetch.mockResolvedValue(jsonResponse(500, {}));

    await expect(createPMSchedule({ asset_code: "211-P-1A" })).rejects.toThrow("Admin Users API unavailable");
  });
});
