import { describe, expect, it } from "vitest";
import buildBusinessBlueprint from "./blueprintBuilder";

describe("buildBusinessBlueprint", () => {
  it("carries the mission input forward as context", () => {
    const blueprint = buildBusinessBlueprint({
      missionInput: "help me run my pump maintenance business",
      answers: { identity: "a pump maintenance company", objective: "no more missed service calls" },
    });

    expect(blueprint.context).toBe("help me run my pump maintenance business");
  });

  it("carries the guided elaboration answers into business identity and objective", () => {
    const blueprint = buildBusinessBlueprint({
      missionInput: "help me run my pump maintenance business",
      answers: { identity: "a pump maintenance company", objective: "no more missed service calls" },
    });

    expect(blueprint.businessIdentity).toBe("a pump maintenance company");
    expect(blueprint.objective).toBe("no more missed service calls");
  });

  it("generates a blueprint id and a captured_at timestamp", () => {
    const blueprint = buildBusinessBlueprint({
      missionInput: "help me run my business",
      answers: { identity: "a business", objective: "success" },
    });

    expect(blueprint.blueprintId).toMatch(/^BLUEPRINT-/);
    expect(() => new Date(blueprint.capturedAt).toISOString()).not.toThrow();
  });
});
