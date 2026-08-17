import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("Pump workspace responsive layout", () => {
  // MWO-LTSA-050 -- same fix Seal.responsive.test.js got in
  // MWO-LTSA-043-RC1: the registry/detail split used to stack only under a
  // 768px media query, sized for the old narrow PumpDetailPanel Card.
  // PumpOpenDesignView is now a wide (max-width: 1240px + 336px Inspector
  // Rail) continuous-document layout, so the side-by-side split would
  // starve it of width on every desktop viewport too -- stacking
  // unconditionally fixes this and still satisfies "stacks on narrow
  // viewports" (a strict superset).
  it("stacks the registry and detail panes unconditionally (column layout)", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "Pump.css"), "utf-8");

    expect(css).toMatch(/\.pump-workspace-layout\s*\{[^}]*flex-direction:\s*column/);
  });
});
