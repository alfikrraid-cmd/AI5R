import { describe, expect, it } from "vitest";

import { mapCurrentCondition } from "./currentConditionMapping";

const raw = (overrides = {}) => ({
  reading_code: "CMONR-1",
  reading_date: "2026-08-13T00:00:00",
  workflow_status: "DRAFT",
  state: "LEAK_DE",
  active: true,
  de: true,
  nde: null,
  completeness: "PARTIAL",
  has_current_reading: true,
  ...overrides,
});

describe("mapCurrentCondition", () => {
  it("maps the backend's canonical current condition without re-deriving it", () => {
    expect(mapCurrentCondition(raw())).toEqual({
      readingCode: "CMONR-1",
      readingDate: "2026-08-13T00:00:00",
      workflowStatus: "DRAFT",
      leakState: "LEAK_DE",
      activeLeak: true,
      leakDe: true,
      leakNde: null,
      completeness: "PARTIAL",
      hasCurrentReading: true,
    });
  });

  it("passes DRAFT/SUBMITTED/FINALIZED through unchanged", () => {
    for (const status of ["DRAFT", "SUBMITTED", "FINALIZED"]) {
      expect(mapCurrentCondition(raw({ workflow_status: status })).workflowStatus).toBe(status);
    }
  });

  it.each([
    ["UNKNOWN", null, null],
    ["NO_LEAK_DE_ONLY", false, null],
    ["NO_LEAK_NDE_ONLY", null, false],
    ["NO_LEAK", false, false],
  ])("keeps %s as-is and not active", (state, de, nde) => {
    const mapped = mapCurrentCondition(raw({ state, active: false, de, nde }));
    expect(mapped.leakState).toBe(state);
    expect(mapped.activeLeak).toBe(false);
    expect(mapped.leakDe).toBe(de);
    expect(mapped.leakNde).toBe(nde);
  });

  it("never reports an active leak for a non-leak state, even if the flag disagrees", () => {
    expect(mapCurrentCondition(raw({ state: "NO_LEAK", active: true })).activeLeak).toBe(false);
  });

  it("treats an unrecognised state as UNKNOWN", () => {
    expect(mapCurrentCondition(raw({ state: "WHATEVER", active: true })).leakState).toBe("UNKNOWN");
  });

  it("represents 'no current reading' explicitly", () => {
    const mapped = mapCurrentCondition(raw({ reading_code: null, reading_date: null, workflow_status: null, state: "UNKNOWN", active: false, de: null, nde: null, completeness: "NOT_RECORDED", has_current_reading: false }));
    expect(mapped).toMatchObject({ hasCurrentReading: false, leakState: "UNKNOWN", activeLeak: false });
  });

  it("returns null when the backend sent no current condition", () => {
    expect(mapCurrentCondition(undefined)).toBeNull();
    expect(mapCurrentCondition(null)).toBeNull();
  });
});
