import { describe, expect, it } from "vitest";
import { WORKSPACE_KEYS, parseWorkspaceLocation, workspaceLocation } from "./WorkspaceRegistry";

// MWO-LTSA-032E -- WorkspaceRegistry: no dedicated test file existed for
// this module before this MWO (confirmed by repository archaeology).
// Covers the pre-existing routes as a regression baseline, plus the new
// Knowledge Workspace route this MWO adds. Pure functions, no React, no
// rendering -- exercises workspaceLocation()/parseWorkspaceLocation()
// directly.

const TAG = "641-P-5";

describe("WorkspaceRegistry -- pre-existing routes (regression baseline)", () => {
  it("builds the Pump (Asset 360) location with a tag", () => {
    expect(workspaceLocation(WORKSPACE_KEYS.PUMP, { assetTag: TAG })).toBe(`/ltsa/pump/${TAG}`);
  });

  it("builds the Pump location with no tag", () => {
    expect(workspaceLocation(WORKSPACE_KEYS.PUMP, {})).toBe("/ltsa/pump-workspace");
  });

  it("builds the Condition Monitoring location", () => {
    expect(workspaceLocation(WORKSPACE_KEYS.CONDITION_MONITORING, { assetTag: TAG })).toBe(
      `/ltsa/pump/${TAG}/monitoring`
    );
  });

  it("builds the Failure Analysis location", () => {
    expect(workspaceLocation(WORKSPACE_KEYS.FAILURE_ANALYSIS, { assetTag: TAG, selectId: "CM-1" })).toBe(
      `/ltsa/pump/${TAG}/failure/CM-1`
    );
  });

  it("parses the Pump-workspace path", () => {
    expect(parseWorkspaceLocation("/ltsa/pump-workspace")).toEqual({ key: WORKSPACE_KEYS.PUMP, context: {} });
  });

  it("parses a bare pump path as Pump with an assetTag", () => {
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}`)).toEqual({
      key: WORKSPACE_KEYS.PUMP,
      context: { assetTag: TAG },
    });
  });

  it("parses the monitoring path", () => {
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}/monitoring`)).toEqual({
      key: WORKSPACE_KEYS.CONDITION_MONITORING,
      context: { assetTag: TAG },
    });
  });

  it("returns null for a non-ltsa path", () => {
    expect(parseWorkspaceLocation("/other/path")).toBeNull();
  });
});

describe("WorkspaceRegistry -- Knowledge Workspace route (MWO-LTSA-032E, new)", () => {
  it("builds the Knowledge Workspace location for a tag", () => {
    expect(workspaceLocation(WORKSPACE_KEYS.KNOWLEDGE, { assetTag: TAG })).toBe(`/ltsa/pump/${TAG}/knowledge`);
  });

  it("parses the Knowledge Workspace path back into key + assetTag", () => {
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}/knowledge`)).toEqual({
      key: WORKSPACE_KEYS.KNOWLEDGE,
      context: { assetTag: TAG },
    });
  });

  it("round-trips workspaceLocation -> parseWorkspaceLocation for Knowledge Workspace", () => {
    const path = workspaceLocation(WORKSPACE_KEYS.KNOWLEDGE, { assetTag: TAG });
    expect(parseWorkspaceLocation(path)).toEqual({ key: WORKSPACE_KEYS.KNOWLEDGE, context: { assetTag: TAG } });
  });

  it("decodes a URL-encoded tag in the Knowledge Workspace path", () => {
    expect(parseWorkspaceLocation("/ltsa/pump/641%2FP%2F5/knowledge")).toEqual({
      key: WORKSPACE_KEYS.KNOWLEDGE,
      context: { assetTag: "641/P/5" },
    });
  });

  it("does not collide with the monitoring or failure routes", () => {
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}/monitoring`).key).toBe(WORKSPACE_KEYS.CONDITION_MONITORING);
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}/failure/CM-1`).key).toBe(WORKSPACE_KEYS.FAILURE_ANALYSIS);
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}/knowledge`).key).toBe(WORKSPACE_KEYS.KNOWLEDGE);
  });
});

describe("WorkspaceRegistry -- Pump Workspace legacy fallback route (MWO-LTSA-036D, new)", () => {
  it("builds the legacy fallback location", () => {
    expect(workspaceLocation(WORKSPACE_KEYS.PUMP_LEGACY, {})).toBe("/ltsa/pump-workspace-legacy");
  });

  it("parses the legacy fallback path back into its key", () => {
    expect(parseWorkspaceLocation("/ltsa/pump-workspace-legacy")).toEqual({
      key: WORKSPACE_KEYS.PUMP_LEGACY,
      context: {},
    });
  });

  it("does not collide with the canonical /ltsa/pump-workspace route", () => {
    expect(parseWorkspaceLocation("/ltsa/pump-workspace").key).toBe(WORKSPACE_KEYS.PUMP);
    expect(parseWorkspaceLocation("/ltsa/pump-workspace-legacy").key).toBe(WORKSPACE_KEYS.PUMP_LEGACY);
  });
});

describe("WorkspaceRegistry -- generic /ltsa/{key} fallback (MWO-LTSA-DASHBOARD-RECOVERY-001, new)", () => {
  it("builds the dashboard location as its own route, not the Pump Workspace fallback", () => {
    expect(workspaceLocation("dashboard", {})).toBe("/ltsa/dashboard");
  });

  it("builds a generic route for any other non-asset-context key", () => {
    expect(workspaceLocation("seal", {})).toBe("/ltsa/seal");
    expect(workspaceLocation("reports", {})).toBe("/ltsa/reports");
  });

  it("parses the dashboard path back into its own key, not Pump", () => {
    expect(parseWorkspaceLocation("/ltsa/dashboard")).toEqual({ key: "dashboard", context: {} });
  });

  it("round-trips workspaceLocation -> parseWorkspaceLocation for the dashboard key", () => {
    const path = workspaceLocation("dashboard", {});
    expect(parseWorkspaceLocation(path)).toEqual({ key: "dashboard", context: {} });
  });

  it("still does not collide with the pump-workspace or asset-context routes", () => {
    expect(parseWorkspaceLocation("/ltsa/pump-workspace").key).toBe(WORKSPACE_KEYS.PUMP);
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}`).key).toBe(WORKSPACE_KEYS.PUMP);
    expect(parseWorkspaceLocation(`/ltsa/pump/${TAG}/monitoring`).key).toBe(WORKSPACE_KEYS.CONDITION_MONITORING);
  });

  it("returns null for a deeper unrecognized path (only exactly /ltsa/{key} matches)", () => {
    expect(parseWorkspaceLocation("/ltsa/dashboard/extra")).toBeNull();
  });

  // Regression: an unbounded "any 2-segment /ltsa/* path is a workspace
  // key" version of this fallback misinterpreted the EXISTING, unrelated
  // /ltsa/{organization} routing convention (ApplicationRouter/
  // OrganizationResolver's own org-slug segment, still present in
  // window.location.pathname when LTSAWorkspace mounts) as a workspace
  // key -- PAGES["tap"] is undefined, crashing ActivePage's render. The
  // generic fallback must stay whitelist-gated to known TABS keys only.
  it("does not treat an organization slug as a workspace key", () => {
    expect(parseWorkspaceLocation("/ltsa/tap")).toBeNull();
    expect(parseWorkspaceLocation("/ltsa/some-other-org-code")).toBeNull();
  });
});
