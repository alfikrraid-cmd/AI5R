import { describe, expect, it } from "vitest";

import { isActiveLeak, LEAK_STATES, leakPresentation, leakPresentationFor, leakState } from "./leakSemantics";

const TRUTH_TABLE = [
  [true, true, "LEAK_DE_AND_NDE"],
  [true, false, "LEAK_DE"],
  [true, null, "LEAK_DE"],
  [false, true, "LEAK_NDE"],
  [null, true, "LEAK_NDE"],
  [false, false, "NO_LEAK"],
  [false, null, "NO_LEAK_DE_ONLY"],
  [null, false, "NO_LEAK_NDE_ONLY"],
  [null, null, "UNKNOWN"],
];

describe("leakState", () => {
  it.each(TRUTH_TABLE)("DE=%s NDE=%s -> %s", (de, nde, expected) => {
    expect(leakState(de, nde)).toBe(expected);
  });

  it("covers every canonical state", () => {
    expect(new Set(TRUTH_TABLE.map(([, , state]) => state))).toEqual(new Set(Object.values(LEAK_STATES)));
  });

  it("treats undefined like null and never coerces it to false", () => {
    expect(leakState(undefined, undefined)).toBe("UNKNOWN");
    expect(leakState(false, undefined)).toBe("NO_LEAK_DE_ONLY");
  });

  it.each(["", 0, 1, "Y", "N", "true"])("does not treat %j as a recorded value", (value) => {
    expect(leakState(value, null)).toBe("UNKNOWN");
    expect(leakState(null, value)).toBe("UNKNOWN");
  });
});

describe("isActiveLeak", () => {
  it.each(Object.values(LEAK_STATES))("%s", (state) => {
    expect(isActiveLeak(state)).toBe(["LEAK_DE", "LEAK_NDE", "LEAK_DE_AND_NDE"].includes(state));
  });
});

describe("leakPresentation", () => {
  it("null/null is Not Recorded, never No Leak, and never the success tone", () => {
    const p = leakPresentationFor(null, null);
    expect(p.state).toBe("UNKNOWN");
    expect(p.label).toBe("Not Recorded");
    expect(p.label).not.toMatch(/No Leak/);
    expect(p.tone).toBe("neutral");
    expect(p.isLeak).toBe(false);
    expect(p.isComplete).toBe(false);
  });

  it("false/null is partial, not confirmed No Leak", () => {
    const p = leakPresentationFor(false, null);
    expect(p.state).toBe("NO_LEAK_DE_ONLY");
    expect(p.label).toBe("No Leak — DE · NDE Not Recorded");
    expect(p.tone).toBe("neutral");
    expect(p.isComplete).toBe(false);
  });

  it("null/false is partial, not confirmed No Leak", () => {
    const p = leakPresentationFor(null, false);
    expect(p.state).toBe("NO_LEAK_NDE_ONLY");
    expect(p.label).toBe("No Leak — NDE · DE Not Recorded");
    expect(p.tone).toBe("neutral");
    expect(p.isComplete).toBe(false);
  });

  it("only a confirmed false/false is No Leak with the normal tone", () => {
    const p = leakPresentationFor(false, false);
    expect(p).toMatchObject({ state: "NO_LEAK", label: "No Leak", tone: "normal", isLeak: false, isComplete: true });
  });

  it.each([
    [true, null, "LEAK_DE", "Leak Detected — DE", "DE", false],
    [true, false, "LEAK_DE", "Leak Detected — DE", "DE", true],
    [null, true, "LEAK_NDE", "Leak Detected — NDE", "NDE", false],
    [false, true, "LEAK_NDE", "Leak Detected — NDE", "NDE", true],
    [true, true, "LEAK_DE_AND_NDE", "Leak Detected — DE & NDE", "DE_AND_NDE", true],
  ])("DE=%s NDE=%s is a critical %s leak on the right side", (de, nde, state, label, side, complete) => {
    const p = leakPresentationFor(de, nde);
    expect(p).toMatchObject({ state, label, side, tone: "critical", isLeak: true, isComplete: complete });
  });

  it("no non-leak, non-confirmed state uses a success/normal tone", () => {
    for (const state of ["NO_LEAK_DE_ONLY", "NO_LEAK_NDE_ONLY", "UNKNOWN"]) {
      expect(leakPresentation(state).tone).toBe("neutral");
    }
  });

  it("falls back to UNKNOWN for an unrecognised state", () => {
    expect(leakPresentation("SOMETHING_ELSE")).toMatchObject({ state: "UNKNOWN", label: "Not Recorded", tone: "neutral" });
  });
});
