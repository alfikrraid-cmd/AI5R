import { describe, expect, it } from "vitest";
import OrganizationContext from "./OrganizationContext";
import OrganizationRegistry from "./OrganizationRegistry";
import { resolveOrganization } from "./OrganizationResolver";

function organization(overrides = {}) {
  return new OrganizationContext({
    organizationId: "tap",
    slug: "tap",
    displayName: "TAP",
    metadata: { region: "id" },
    ...overrides,
  });
}

describe("OrganizationContext", () => {
  it("creates an immutable platform-owned organization context", () => {
    const context = organization();

    expect(context.organizationId).toBe("tap");
    expect(context.slug).toBe("tap");
    expect(context.displayName).toBe("TAP");
    expect(context.metadata).toEqual({ region: "id" });
    expect(Object.isFrozen(context)).toBe(true);
    expect(Object.isFrozen(context.metadata)).toBe(true);
  });

  it("requires canonical organization fields", () => {
    expect(() => organization({ organizationId: "" })).toThrow("organizationId is required");
    expect(() => organization({ slug: "" })).toThrow("slug is required");
    expect(() => organization({ displayName: "" })).toThrow("displayName is required");
  });
});

describe("OrganizationRegistry", () => {
  it("registers, gets, lists, and checks organization contexts", () => {
    const registry = new OrganizationRegistry();
    const context = organization();

    expect(registry.exists("tap")).toBe(false);
    expect(registry.register(context)).toBe(context);
    expect(registry.exists("tap")).toBe(true);
    expect(registry.get("tap")).toBe(context);
    expect(registry.list()).toEqual([context]);
  });
});

describe("OrganizationResolver", () => {
  it("resolves organization context from the first non-reserved path segment after the base path", () => {
    const context = resolveOrganization({
      pathname: "/ltsa/tap",
      basePath: "/ltsa",
      reservedRouteSegments: ["pump", "pump-workspace"],
    });

    expect(context).toEqual(
      new OrganizationContext({
        organizationId: "tap",
        slug: "tap",
        displayName: "TAP",
        metadata: {},
      })
    );
  });

  it("does not resolve an organization for the base application path", () => {
    expect(resolveOrganization({ pathname: "/ltsa", basePath: "/ltsa" })).toBeNull();
  });

  it("does not resolve reserved product workspace segments as organizations", () => {
    const context = resolveOrganization({
      pathname: "/ltsa/pump/641-P-5",
      basePath: "/ltsa",
      reservedRouteSegments: ["pump", "pump-workspace", "pump-workspace-legacy", "pm-workspace"],
    });

    expect(context).toBeNull();
  });

  it("does not resolve paths outside the application base path", () => {
    expect(resolveOrganization({ pathname: "/auditor/tap", basePath: "/ltsa" })).toBeNull();
  });
});
