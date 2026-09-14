import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("Condition Monitoring workspace responsive layout", () => {
  // UI-D2C -- same fix Pump.css/Seal.css/WorkOrder.css/PM.css already got:
  // the registry/detail split used to stack only under a 768px media
  // query, sized for the old narrow detail Card. ConditionMonitoringOpenDesignView
  // is now a wide (max-width: 1240px) continuous-document layout, so the
  // side-by-side split would starve it of width on every desktop viewport
  // too -- stacking unconditionally fixes this and still satisfies "stacks
  // on narrow viewports" (a strict superset).
  it("stacks the registry and detail panes unconditionally (column layout)", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "ConditionMonitoring.css"), "utf-8");

    expect(css).toMatch(/\.cmon-workspace-layout\s*\{[^}]*flex-direction:\s*column/);
  });

  // UI-D2C -- same "hide dense table, show compact cards" mobile pattern
  // UI-D2A.1/UI-D2B established for Work Order/PM's own Readings-equivalent
  // registry (ConditionMonitoringReadingTable.jsx).
  it("hides the desktop table and shows the mobile card list under the 768px breakpoint", () => {
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(path.join(dir, "ConditionMonitoring.css"), "utf-8");

    expect(css).toMatch(/@media \(max-width: 768px\)\s*\{[^]*\.cmon-table-wrap\s*\{[^}]*display:\s*none/);
    expect(css).toMatch(/\.cmon-registry\[data-collapsed="true"\]\s*\.cmon-card-list\s*\{[^}]*display:\s*none/);
    expect(css).toMatch(/\.cmon-registry\[data-collapsed="true"\]\s*\.cmon-collapsed-summary\s*\{[^}]*display:\s*flex/);
  });
});
