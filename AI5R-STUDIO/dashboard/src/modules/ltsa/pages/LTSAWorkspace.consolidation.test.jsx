import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";
import { ROLES, TAB_PERMISSIONS, visibleTabKeys } from "../auth/permissions";

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

  it("MaintenanceHistory.jsx remains wired at its explicit legacy fallback route -- not orphaned, per MWO-LTSA-036H/036J's own findings", () => {
    const source = readSource("LTSAWorkspace.jsx");

    expect(source).toMatch(/from ["']\.\/MaintenanceHistory["']/);
    expect(source).toMatch(/"history-legacy":\s*MaintenanceHistory/);
  });

  // MWO-LTSA-DEMO-READINESS-CLOSURE-001 -- superseded MWO-LTSA-036G's
  // "untagged 'history' falls back to MaintenanceHistory's own picker+
  // full page" design: that fallback rendered MaintenanceHistory's entire
  // separate legacy experience (own breadcrumb "Pumps > {tag}", own
  // PumpWorkspaceTimeline with its own "No history matches this filter."
  // empty state, own "Coming Soon"/"Not available" placeholders) once a
  // pump was picked, not just to resolve the asset -- confirmed as the
  // root cause of a demo-facing symptom where the untagged entry point
  // could show an entirely different, non-canonical screen for a
  // different pump. AssetLauncher now owns the untagged picker (reusing
  // AssetSelector.jsx + getPumps, no new engine); MaintenanceHistory.jsx
  // itself is untouched and stays reachable only at its own explicit
  // "history-legacy" route (locked in by the test above).
  it("the untagged 'history' entry point no longer hands off to MaintenanceHistory's own rendering -- AssetLauncher does, converging on canonical KnowledgeWorkspace", () => {
    const source = readSource("LTSAWorkspace.jsx");

    expect(source).not.toMatch(/<MaintenanceHistory /);
    expect(source).toMatch(/<AssetLauncher /);
  });
});

// LTSA_PERTAMINA_ENGINEER_REACT_130_FIX_R4 -- TAB_PERMISSIONS kept a stale
// "equipment" key after its page was retired, so every role without
// dashboard access landed on PAGES["equipment"] === undefined (React #130,
// blank /ltsa). These lock in that every permission-visible key is backed by
// a real PAGES entry, for every role's real backend permission array.
function pagesKeys() {
  const pagesBlock = readSource("LTSAWorkspace.jsx").match(/const PAGES = \{([\s\S]*?)\n\};/)[1];
  return new Set([...pagesBlock.matchAll(/^\s*"?([\w-]+)"?:/gm)].map((match) => match[1]));
}

// Mirrors LTSAAuthGate.jsx's DEFAULT_LANDING_KEY fallback.
function landingKey(keys) {
  return keys.includes("dashboard") ? "dashboard" : keys[0];
}

// Verbatim CORE-SERVICES/API/auth_service.py ROLE_PERMISSIONS, as served by
// GET /api/auth/me for the three roles that previously crashed.
const BACKEND_PERMISSIONS = {
  [ROLES.PERTAMINA_ENGINEER]: [
    "condition.read", "drawing.read", "engineering_ai.ask", "inventory.read",
    "maintenance.read", "pump.read", "seal.read",
  ],
  [ROLES.PERTAMINA_VIEWER]: ["inventory.read", "maintenance.read", "pump.read", "seal.read"],
  [ROLES.JOHN_CRANE_ENGINEER]: [
    "condition.read", "drawing.read", "engineering_ai.ask", "internal_component.read",
    "inventory.read", "maintenance.read", "maintenance.technical_review", "pump.read", "seal.read",
  ],
};

describe("TAB_PERMISSIONS / PAGES consistency (LTSA_PERTAMINA_ENGINEER_REACT_130_FIX_R4)", () => {
  it("every TAB_PERMISSIONS key is backed by a real PAGES entry", () => {
    const pages = pagesKeys();
    const orphaned = Object.keys(TAB_PERMISSIONS).filter((key) => !pages.has(key));

    expect(orphaned).toEqual([]);
  });

  it("the retired Equipment page is not restored and no longer gated", () => {
    expect(TAB_PERMISSIONS).not.toHaveProperty("equipment");
    expect(pagesKeys().has("equipment")).toBe(false);
  });

  it("every role's visible keys resolve to real pages, under fallback and real backend sessions", () => {
    const pages = pagesKeys();
    const sessions = [
      ...Object.values(ROLES).map((role) => ({ role })),
      ...Object.entries(BACKEND_PERMISSIONS).map(([role, permissions]) => ({ role, permissions })),
    ];

    sessions.forEach((session) => {
      const keys = visibleTabKeys(session);
      expect(keys.length).toBeGreaterThan(0);
      keys.forEach((key) => expect(pages.has(key)).toBe(true));
      expect(pages.has(landingKey(keys))).toBe(true);
    });
  });

  it.each(Object.keys(BACKEND_PERMISSIONS))(
    "%s (real backend permissions) lands on pump, a real page, with no equipment key",
    (role) => {
      const keys = visibleTabKeys({ role, permissions: BACKEND_PERMISSIONS[role] });

      expect(keys).not.toContain("equipment");
      expect(keys).not.toContain("dashboard");
      expect(landingKey(keys)).toBe("pump");
      expect(pagesKeys().has(landingKey(keys))).toBe(true);
    }
  );
});
