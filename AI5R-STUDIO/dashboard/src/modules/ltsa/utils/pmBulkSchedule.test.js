import { describe, expect, it } from "vitest";
import {
  SUPPORTED_FREQUENCIES,
  countPlannedActivities,
  deriveTriggerType,
  emptyBulkRow,
  toBulkCreatePayload,
  toBulkCreatePayloadRow,
  validateBulkRows,
} from "./pmBulkSchedule";

const PUMPS = new Set(["211-P-1A", "211-P-1B", "533-P-1"]);

function row(overrides = {}) {
  return { ...emptyBulkRow(overrides.id || "row-1"), ...overrides };
}

describe("deriveTriggerType", () => {
  it("derives CALENDAR for DAILY/WEEKLY/MONTHLY and METER for RUNTIME_BASED", () => {
    expect(deriveTriggerType("DAILY")).toBe("CALENDAR");
    expect(deriveTriggerType("WEEKLY")).toBe("CALENDAR");
    expect(deriveTriggerType("MONTHLY")).toBe("CALENDAR");
    expect(deriveTriggerType("RUNTIME_BASED")).toBe("METER");
  });
});

describe("emptyBulkRow", () => {
  it("starts with every planned activity unchecked and no pump selected", () => {
    const r = emptyBulkRow("row-1");
    expect(r.pumpTag).toBe("");
    expect(r.plannedMap).toEqual({});
    expect(r.selected).toBe(false);
  });
});

describe("validateBulkRows -- required fields (ERROR)", () => {
  it("flags a missing pump as an error", () => {
    const { results, summary } = validateBulkRows([row({ pumpTag: "" })], { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("ERROR");
    expect(results["row-1"].errors).toContain("Pump is required.");
    expect(summary).toEqual({ rows: 1, ready: 0, warnings: 0, errors: 1 });
  });

  it("flags an unknown/noncanonical pump as an error", () => {
    const { results } = validateBulkRows([row({ pumpTag: "NOT-REAL" })], { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("ERROR");
    expect(results["row-1"].errors[0]).toMatch(/Unknown pump/);
  });

  it("flags a missing frequency as an error", () => {
    const { results } = validateBulkRows([row({ pumpTag: "211-P-1A", frequency: "" })], { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("ERROR");
  });

  it("flags an unsupported frequency as an error", () => {
    const { results } = validateBulkRows([row({ pumpTag: "211-P-1A", frequency: "YEARLY" })], {
      canonicalPumpTags: PUMPS,
    });
    expect(results["row-1"].level).toBe("ERROR");
  });

  it("flags a missing start date as an error", () => {
    const { results } = validateBulkRows([row({ pumpTag: "211-P-1A", startDate: "" })], { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("ERROR");
  });

  it("flags a negative duration as an error", () => {
    const { results } = validateBulkRows([row({ pumpTag: "211-P-1A", duration: "-5" })], { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("ERROR");
  });

  it("allows a blank duration (optional field)", () => {
    const { results } = validateBulkRows([row({ pumpTag: "211-P-1A", duration: "" })], { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("READY");
  });

  it("flags a structurally-invalid Reservoir DE/NDE selection as an error", () => {
    const { results } = validateBulkRows(
      [row({ pumpTag: "211-P-1A", plannedMap: { RESERVOIR_DE: true } })],
      { canonicalPumpTags: PUMPS }
    );
    expect(results["row-1"].level).toBe("ERROR");
  });
});

describe("validateBulkRows -- within-batch duplicates", () => {
  it("flags an exact pump+frequency+startDate duplicate as an error, only on the second occurrence", () => {
    const rows = [
      row({ id: "row-1", pumpTag: "211-P-1A", frequency: "MONTHLY", startDate: "2026-10-01" }),
      row({ id: "row-2", pumpTag: "211-P-1A", frequency: "MONTHLY", startDate: "2026-10-01" }),
    ];
    const { results, summary } = validateBulkRows(rows, { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("READY");
    expect(results["row-2"].level).toBe("ERROR");
    expect(summary).toEqual({ rows: 2, ready: 1, warnings: 0, errors: 1 });
  });

  it("does not flag the same pump+frequency with a different start date as an error (only a warning)", () => {
    const rows = [
      row({ id: "row-1", pumpTag: "211-P-1A", frequency: "MONTHLY", startDate: "2026-10-01" }),
      row({ id: "row-2", pumpTag: "211-P-1A", frequency: "MONTHLY", startDate: "2026-11-01" }),
    ];
    const { results } = validateBulkRows(rows, { canonicalPumpTags: PUMPS });
    expect(results["row-1"].level).toBe("READY");
    expect(results["row-2"].level).toBe("WARNING");
  });

  it("does not flag different pumps or different frequencies as duplicates", () => {
    const rows = [
      row({ id: "row-1", pumpTag: "211-P-1A", frequency: "MONTHLY", startDate: "2026-10-01" }),
      row({ id: "row-2", pumpTag: "211-P-1B", frequency: "MONTHLY", startDate: "2026-10-01" }),
      row({ id: "row-3", pumpTag: "211-P-1A", frequency: "WEEKLY", startDate: "2026-10-01" }),
    ];
    const { summary } = validateBulkRows(rows, { canonicalPumpTags: PUMPS });
    expect(summary.errors).toBe(0);
  });
});

describe("validateBulkRows -- overlap warning (deferred, soft heuristic)", () => {
  it("warns when an ACTIVE schedule already exists for the same pump+frequency, without blocking", () => {
    const existingActiveSchedules = [{ equipmentTag: "211-P-1A", frequency: "MONTHLY", status: "ACTIVE" }];
    const { results, summary } = validateBulkRows([row({ pumpTag: "211-P-1A", frequency: "MONTHLY" })], {
      canonicalPumpTags: PUMPS,
      existingActiveSchedules,
    });
    expect(results["row-1"].level).toBe("WARNING");
    expect(summary.errors).toBe(0);
    expect(summary.warnings).toBe(1);
  });

  it("does not warn for a non-ACTIVE existing schedule (COMPLETED/CANCELLED)", () => {
    const existingActiveSchedules = [{ equipmentTag: "211-P-1A", frequency: "MONTHLY", status: "COMPLETED" }];
    const { results } = validateBulkRows([row({ pumpTag: "211-P-1A", frequency: "MONTHLY" })], {
      canonicalPumpTags: PUMPS,
      existingActiveSchedules,
    });
    expect(results["row-1"].level).toBe("READY");
  });
});

describe("toBulkCreatePayloadRow / toBulkCreatePayload", () => {
  it("maps a row to the exact wire shape, with Notes -> procedure and derived trigger_type", () => {
    const r = row({
      pumpTag: "211-P-1A",
      frequency: "RUNTIME_BASED",
      startDate: "2026-10-01",
      technician: "Bagus Setiawan",
      duration: "2.5",
      notes: "Bring spare gasket",
    });
    const payload = toBulkCreatePayloadRow(r);
    expect(payload).toEqual({
      client_row_id: "row-1",
      asset_code: "211-P-1A",
      procedure: "Bring spare gasket",
      frequency: "RUNTIME_BASED",
      trigger_type: "METER",
      effective_date: "2026-10-01",
      next_due: "2026-10-01",
      assigned_to: "Bagus Setiawan",
      estimated_duration_hours: 2.5,
      planned_activities: null,
    });
  });

  it("includes explicitly checked planned activities with no `done` field and no legacy numeric code", () => {
    const r = row({ pumpTag: "211-P-1A", plannedMap: { FLUSHING_LINE_DE: true, RESERVOIR: true } });
    const payload = toBulkCreatePayloadRow(r);
    expect(payload.planned_activities).toEqual([
      { family: "Flushing Line", variant: "DE", code: "FLUSHING_LINE_DE" },
      { family: "Reservoir", variant: "GENERAL", code: "RESERVOIR" },
    ]);
    for (const entry of payload.planned_activities) {
      expect(entry).not.toHaveProperty("done");
      expect(entry.code).not.toMatch(/^\d+$/);
    }
  });

  it("builds a { rows: [...] } request body for the whole batch", () => {
    const rows = [row({ id: "row-1", pumpTag: "211-P-1A" }), row({ id: "row-2", pumpTag: "211-P-1B" })];
    const payload = toBulkCreatePayload(rows);
    expect(payload.rows).toHaveLength(2);
    expect(payload.rows.map((r) => r.client_row_id)).toEqual(["row-1", "row-2"]);
  });
});

describe("countPlannedActivities", () => {
  it("counts only checked entries", () => {
    expect(countPlannedActivities({ FLUSHING_LINE: true, RESERVOIR: false, COOLER: true })).toBe(2);
    expect(countPlannedActivities({})).toBe(0);
  });
});

describe("SUPPORTED_FREQUENCIES", () => {
  it("is exactly the four backend-supported values", () => {
    expect(SUPPORTED_FREQUENCIES).toEqual(["DAILY", "WEEKLY", "MONTHLY", "RUNTIME_BASED"]);
  });
});
