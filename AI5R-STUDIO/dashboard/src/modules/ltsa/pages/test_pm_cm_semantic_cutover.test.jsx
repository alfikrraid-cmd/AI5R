import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";
import { parseWorkspaceLocation, workspaceLocation } from "../workspace/WorkspaceRegistry";

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSource(filename) {
  return readFileSync(resolve(__dirname, filename), "utf-8");
}

describe("LTSA PM/CM Semantic Cutover R1 (Frontend)", () => {
  it("A. Navigation has one canonical CM entry: CM = Condition Monitoring, and NO Corrective Maintenance tab", () => {
    const source = readSource("LTSAWorkspace.jsx");
    const tabsMatch = source.match(/const TABS = \[([\s\S]*?)\n\];/);
    expect(tabsMatch).toBeTruthy();
    const tabsBlock = tabsMatch[1];

    // Canonical CM tab exists
    expect(tabsBlock).toMatch(/\{\s*key:\s*"cm",\s*label:\s*"Condition Monitoring"\s*\}/);

    // No Corrective Maintenance tab in TABS
    expect(tabsBlock).not.toMatch(/Corrective Maintenance/);
    // No cmon key in TABS
    expect(tabsBlock).not.toMatch(/key:\s*"cmon"/);

    // PRIMARY_NAV_KEYS includes "cm" instead of "cmon"
    const navMatch = source.match(/const PRIMARY_NAV_KEYS = \[([\s\S]*?)\n\];/);
    expect(navMatch).toBeTruthy();
    const navBlock = navMatch[1];
    expect(navBlock).toContain('"cm"');
    expect(navBlock).not.toContain('"cmon"');
  });

  it("B. ConditionMonitoring workspace opens through canonical CM route and PAGES['cm'] mounts ConditionMonitoring", () => {
    const source = readSource("LTSAWorkspace.jsx");
    const pagesMatch = source.match(/const PAGES = \{([\s\S]*?)\n\};/);
    expect(pagesMatch).toBeTruthy();
    const pagesBlock = pagesMatch[1];

    // cm mounts ConditionMonitoring
    expect(pagesBlock).toMatch(/cm:\s*ConditionMonitoring/);
    // Legacy CM.jsx is not mounted
    expect(pagesBlock).not.toMatch(/cm:\s*CM[, \n]/);
    expect(source).not.toMatch(/import CM from ["']\.\/CM["']/);
  });

  it("C. Legacy cmon route remains compatible and resolves to cm", () => {
    const parsedCmon = parseWorkspaceLocation("/ltsa/cmon");
    expect(parsedCmon).toBeTruthy();
    expect(parsedCmon.key).toBe("cm");

    const parsedCm = parseWorkspaceLocation("/ltsa/cm");
    expect(parsedCm).toBeTruthy();
    expect(parsedCm.key).toBe("cm");
  });

  it("D. KnowledgeUnifiedHistory: CM = Condition Monitoring, no user-facing CMON or Corrective Maintenance badge", () => {
    const source = readFileSync(resolve(__dirname, "../components/KnowledgeUnifiedHistory.jsx"), "utf-8");

    // Filter options has CM
    expect(source).toMatch(/\{\s*key:\s*"CM",\s*label:\s*"CM"\s*\}/);
    // No CMON badge in filter options
    expect(source).not.toMatch(/\{\s*key:\s*"CMON",\s*label:\s*"CMON"\s*\}/);

    // Label mapping: CM maps to CONDITION MONITORING
    expect(source).toMatch(/CM:\s*"CONDITION MONITORING"/);
    expect(source).not.toMatch(/CM:\s*"CORRECTIVE MAINTENANCE"/);
  });

  it("E. CopilotPanel does not expose Corrective Maintenance", () => {
    const source = readFileSync(resolve(__dirname, "../components/CopilotPanel.jsx"), "utf-8");
    expect(source).not.toMatch(/cm:\s*"Corrective Maintenance"/);
  });
});
