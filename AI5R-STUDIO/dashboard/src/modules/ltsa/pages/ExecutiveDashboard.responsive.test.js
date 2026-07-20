import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("Executive Dashboard responsive layout", () => {
  it("defines narrow-viewport media queries that collapse the KPI grid", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "ExecutiveDashboard.css"), "utf-8");

    expect(css).toMatch(/@media \(max-width: 768px\)/);
    expect(css).toMatch(/@media \(max-width: 480px\)/);
    expect(css).toMatch(/grid-template-columns:\s*1fr/);
  });
});
