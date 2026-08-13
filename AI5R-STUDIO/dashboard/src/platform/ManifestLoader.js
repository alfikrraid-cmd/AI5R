import ApplicationDescriptor from "./ApplicationDescriptor";
import PlatformRegistry from "./PlatformRegistry";

const APPLICATION_MANIFEST = [
  {
    applicationId: "platform-home",
    displayName: "AI5ROS",
    basePath: "/",
    status: "active",
    organizationAware: false,
    entry: "platform-home",
    reservedRouteSegments: [],
    defaultPath: "/",
    slug: "",
  },
  {
    applicationId: "ltsa",
    displayName: "LTSA",
    basePath: "/ltsa",
    status: "active",
    organizationAware: true,
    entry: "ltsa",
    reservedRouteSegments: ["pump", "pump-workspace", "pump-workspace-legacy", "pm-workspace"],
    defaultPath: "/ltsa/pump-workspace",
    slug: "ltsa",
  },
  {
    applicationId: "od",
    displayName: "Open Design",
    basePath: "/od",
    status: "active",
    organizationAware: false,
    entry: "od",
    reservedRouteSegments: [],
    defaultPath: "/od",
    slug: "od",
  },
];

export function loadApplicationDescriptors(manifest = APPLICATION_MANIFEST) {
  return manifest.map((application) => new ApplicationDescriptor(application));
}

export function loadPlatformRegistry(manifest = APPLICATION_MANIFEST) {
  const registry = new PlatformRegistry();
  for (const descriptor of loadApplicationDescriptors(manifest)) {
    registry.register(descriptor);
  }
  return registry;
}
