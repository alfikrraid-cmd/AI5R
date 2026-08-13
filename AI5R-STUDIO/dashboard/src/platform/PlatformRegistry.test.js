import { describe, expect, it } from "vitest";
import ApplicationDescriptor from "./ApplicationDescriptor";
import { loadApplicationDescriptors, loadPlatformRegistry } from "./ManifestLoader";
import PlatformRegistry from "./PlatformRegistry";

function descriptor(overrides = {}) {
  return new ApplicationDescriptor({
    applicationId: "app-1",
    displayName: "Application 1",
    basePath: "/app-1",
    status: "active",
    organizationAware: false,
    entry: "app-1",
    reservedRouteSegments: ["workspace"],
    ...overrides,
  });
}

describe("ApplicationDescriptor", () => {
  it("creates an immutable generic application descriptor", () => {
    const application = descriptor();

    expect(application.applicationId).toBe("app-1");
    expect(application.reservedRouteSegments).toEqual(["workspace"]);
    expect(Object.isFrozen(application)).toBe(true);
    expect(Object.isFrozen(application.reservedRouteSegments)).toBe(true);
  });

  it("requires generic descriptor fields", () => {
    expect(() => descriptor({ applicationId: "" })).toThrow("applicationId is required");
    expect(() => descriptor({ entry: "" })).toThrow("entry is required");
  });
});

describe("PlatformRegistry", () => {
  it("registers, gets, lists, and checks application descriptors", () => {
    const registry = new PlatformRegistry();
    const application = descriptor();

    expect(registry.exists("app-1")).toBe(false);
    expect(registry.register(application)).toBe(application);
    expect(registry.exists("app-1")).toBe(true);
    expect(registry.get("app-1")).toBe(application);
    expect(registry.list()).toEqual([application]);
  });

  it("stores application descriptors only, not product internals", () => {
    const registry = loadPlatformRegistry();
    const ltsa = registry.get("ltsa");

    expect(ltsa.entry).toBe("ltsa");
    expect(ltsa.reservedRouteSegments).toContain("pump");
    expect(ltsa.WorkspaceRegistry).toBeUndefined();
    expect(ltsa.LTSAWorkspace).toBeUndefined();
  });
});

describe("ManifestLoader", () => {
  it("loads application descriptors read-only", () => {
    const descriptors = loadApplicationDescriptors([
      {
        applicationId: "app-2",
        displayName: "Application 2",
        basePath: "/app-2",
        status: "active",
        organizationAware: true,
        entry: "app-2",
        reservedRouteSegments: ["item"],
      },
    ]);

    expect(descriptors).toHaveLength(1);
    expect(descriptors[0]).toBeInstanceOf(ApplicationDescriptor);
    expect(descriptors[0].organizationAware).toBe(true);
  });

  it("loads the canonical platform applications into a registry", () => {
    const registry = loadPlatformRegistry();

    expect(registry.exists("platform-home")).toBe(true);
    expect(registry.exists("ltsa")).toBe(true);
    expect(registry.exists("od")).toBe(true);
    expect(registry.list().map((application) => application.applicationId)).toEqual([
      "platform-home",
      "ltsa",
      "od",
    ]);
  });
});
