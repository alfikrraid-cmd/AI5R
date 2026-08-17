import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("Maintenance History workspace responsive layout", () => {
  it("defines narrow-viewport media queries that stack and compact the layout", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "MaintenanceHistory.css"), "utf-8");

    expect(css).toMatch(/@media \(max-width: 980px\)/);
    expect(css).toMatch(/grid-template-columns:\s*1fr/);
    expect(css).toMatch(/@media \(max-width: 640px\)/);
  });
});
