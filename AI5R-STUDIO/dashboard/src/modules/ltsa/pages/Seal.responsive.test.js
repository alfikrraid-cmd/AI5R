import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("Seal workspace responsive layout", () => {
  it("defines a narrow-viewport media query that stacks the layout", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "Seal.css"), "utf-8");

    expect(css).toMatch(/@media \(max-width: 768px\)/);
    expect(css).toMatch(/flex-direction:\s*column/);
  });
});
