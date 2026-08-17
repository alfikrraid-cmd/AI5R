export default class ApplicationDescriptor {
  constructor({
    applicationId,
    displayName,
    basePath,
    status,
    organizationAware = false,
    entry,
    reservedRouteSegments = [],
    defaultPath,
    slug,
    standalone = false,
  }) {
    if (!applicationId) {
      throw new Error("applicationId is required");
    }
    if (!displayName) {
      throw new Error("displayName is required");
    }
    if (!basePath) {
      throw new Error("basePath is required");
    }
    if (!status) {
      throw new Error("status is required");
    }
    if (!entry) {
      throw new Error("entry is required");
    }

    this.applicationId = applicationId;
    this.displayName = displayName;
    this.basePath = basePath;
    this.status = status;
    this.organizationAware = Boolean(organizationAware);
    this.entry = entry;
    this.reservedRouteSegments = Object.freeze([...reservedRouteSegments]);
    this.defaultPath = defaultPath ?? basePath;
    this.slug = slug ?? basePath.replace(/^\//, "");
    // MWO-LTSA-STANDALONE-PRODUCT-SHELL-001 -- an application that owns its
    // own product shell (auth chrome, identity header, navigation) end to
    // end, so the platform must not additionally wrap it in Studio's own
    // DashboardLayout/ProductChrome. False for every pre-existing
    // application (unchanged rendering).
    this.standalone = Boolean(standalone);

    Object.freeze(this);
  }
}
