import { describe, expect, it } from "vitest";
import shadows from "./shadows";

describe("theme/shadows", () => {
  it("defines an sm/md/lg elevation scale as CSS box-shadow strings", () => {
    ["sm", "md", "lg"].forEach((key) => {
      expect(typeof shadows[key]).toBe("string");
      expect(shadows[key]).toMatch(/rgba?\(/);
    });
  });
});
