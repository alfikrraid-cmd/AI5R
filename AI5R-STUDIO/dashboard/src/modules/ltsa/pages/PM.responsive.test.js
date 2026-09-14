import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("PM workspace responsive layout", () => {
  // UI-D2B -- same fix Pump.css/Seal.css/WorkOrder.css already got: the
  // registry/detail split used to stack only under a 768px media query,
  // sized for the old narrow PMDetailPanel Card. PMOpenDesignView is now a
  // wide (max-width: 1240px) continuous-document layout, so the side-by-
  // side split would starve it of width on every desktop viewport too --
  // stacking unconditionally fixes this and still satisfies "stacks on
  // narrow viewports" (a strict superset).
  it("stacks the registry and detail panes unconditionally (column layout)", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "PM.css"), "utf-8");

    expect(css).toMatch(/\.pm-workspace-layout\s*\{[^}]*flex-direction:\s*column/);
  });
});
