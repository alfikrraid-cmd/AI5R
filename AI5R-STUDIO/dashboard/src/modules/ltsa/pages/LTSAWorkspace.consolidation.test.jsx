import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";

// MWO-LTSA-036M -- Consolidate LTSA workspaces. Source-text assertions
// (not render-based), mirroring the established precedent
// MaintenanceHistory.responsive.test.js already uses for "assert a fact
// about a file's real content" checks -- avoids duplicating
// LTSAWorkspace.test.jsx's large API-mock setup for facts that don't
// require rendering anything.
//
// Repository Archaeology (this MWO) found every *.jsx page file under
// pages/ is reachable except one: PMWorkspace.jsx (96 lines, every
// section a PumpWorkspaceComingSoon placeholder, zero data fetching, zero
// props) is not imported by LTSAWorkspace.jsx, has no test file, and
// nothing else in the module references it. PMWorkOrderWorkspace.jsx
// (591 lines, real data, wired at PAGES["pm-workspace"]) is the real,
// substantially-built implementation of the same "PM execution
// workspace" concept -- PMWorkspace.jsx is its superseded, orphaned
// precursor. Per this mission's "Never delete code" rule, PMWorkspace.jsx
// is left on disk, untouched; these tests lock in that it correctly
// stays unreferenced rather than being silently re-wired by accident.

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSource(filename) {
  return readFileSync(resolve(__dirname, filename), "utf-8");
}

describe("LTSA workspace consolidation (MWO-LTSA-036M)", () => {
  it("PMWorkspace.jsx (orphaned, superseded placeholder) is not imported by LTSAWorkspace.jsx", () => {
    const source = readSource("LTSAWorkspace.jsx");

    expect(source).not.toMatch(/from ["']\.\/PMWorkspace["']/);
  });

  it("PMWorkOrderWorkspace.jsx (the canonical PM execution workspace) is imported and wired into PAGES", () => {
    const source = readSource("LTSAWorkspace.jsx");

    expect(source).toMatch(/from ["']\.\/PMWorkOrderWorkspace["']/);
    expect(source).toMatch(/"pm-workspace":\s*PMWorkOrderWorkspace/);
  });

  it("every TABS key has a corresponding PAGES entry", () => {
    const source = readSource("LTSAWorkspace.jsx");
    const tabsBlock = source.match(/const TABS = \[([\s\S]*?)\n\];/)[1];
    const keys = [...tabsBlock.matchAll(/key:\s*"([^"]+)"/g)].map((match) => match[1]);
    const pagesBlock = source.match(/const PAGES = \{([\s\S]*?)\n\};/)[1];

    expect(keys.length).toBeGreaterThan(0);
    keys.forEach((key) => {
      // MWO-LTSA-HISTORICAL-REVIEW-UI-001 -- a hyphenated TABS key (e.g.
      // "historical-review") is only valid as a QUOTED PAGES object key
      // ("historical-review": ...), unlike every single-word key before
      // it (bare, e.g. dashboard: ...). Matches either form, anchored to
      // start-of-line/whitespace so it never matches inside a longer key.
      expect(pagesBlock).toMatch(new RegExp(`(^|\\s)"?${key}"?:`, "m"));
    });
  });

  it("the 5 report sub-pages are reachable indirectly via ReportsWorkspace.jsx, not orphaned", () => {
    const source = readSource("ReportsWorkspace.jsx");
    const reportPages = [
      "ExecutiveSummaryReport",
      "PumpHistoryReport",
      "WorkOrderReport",
      "PreventiveMaintenanceReport",
      "CorrectiveMaintenanceReport",
    ];

    reportPages.forEach((name) => {
      expect(source).toMatch(new RegExp(`from ["']\\./${name}["']`));
    });
  });

  it("MaintenanceHistory.jsx remains wired (legacy fallback + untagged-entry picker) -- not orphaned, per MWO-LTSA-036H/036J/036G's own findings", () => {
    const source = readSource("LTSAWorkspace.jsx");

    expect(source).toMatch(/from ["']\.\/MaintenanceHistory["']/);
    expect(source).toMatch(/"history-legacy":\s*MaintenanceHistory/);
    expect(source).toMatch(/<MaintenanceHistory /);
  });
});
